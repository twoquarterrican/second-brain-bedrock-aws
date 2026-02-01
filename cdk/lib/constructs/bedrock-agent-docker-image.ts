import * as cdk from 'aws-cdk-lib/core';
import {Construct} from 'constructs/lib/construct';
import * as ecr_assets from 'aws-cdk-lib/aws-ecr-assets';
import { Platform } from 'aws-cdk-lib/aws-ecr-assets';
import * as path from "node:path";
import * as fs from 'node:fs';

export interface Props {
    appName: string
}

/**
 * Constructs and publishes a Docker image for the Bedrock agent to ECR.
 *
 * ## Problem Solved: Docker Build Context Management
 *
 * When Docker builds an image, it needs access to a "build context" - a directory tree that
 * contains all files the Dockerfile might reference (COPY, ADD commands, etc.). Docker sends
 * the entire build context to the Docker daemon, which can be extremely slow and consume
 * massive amounts of resources if the directory tree is large.
 *
 * In monorepos or large projects, the build context can easily become huge:
 * - Node modules (node_modules/) can be 100MB-1GB+
 * - Git history (.git/) can be hundreds of MB
 * - Build artifacts (dist/, build/, .next/) can be large
 * - Caches (__pycache__/, .pytest_cache/, etc.) add unnecessary overhead
 * - Logs, documentation, and other unrelated files all get included
 *
 * Relying on .dockerignore to exclude these files is error-prone because:
 * 1. It's easy to forget to add entries when adding new directories
 * 2. It's not explicit about what IS needed (blacklist vs whitelist approach)
 * 3. Different Docker build contexts might need different .dockerignore files
 * 4. It's not obvious to developers why certain entries are there
 *
 * ## Solution: Explicit Build Context Construction
 *
 * This construct creates an explicit, minimal Docker build context by:
 * 1. Creating a temporary directory to serve as the build context
 * 2. Copying ONLY the files the Dockerfile needs:
 *    - Root-level pyproject.toml (for workspace configuration)
 *    - packages/bedrock/ (with its pyproject.toml and src/)
 *    - packages/shared/ (with its pyproject.toml and src/)
 *    - The Dockerfile itself
 * 3. Explicitly excluding all build cache directories (no guessing)
 * 4. Passing this minimal directory as the build context to Docker
 *
 * This ensures:
 * - Build context size is predictable and minimal (~10-100 MB instead of 37+ GB)
 * - Build time is fast and consistent
 * - Future project changes won't accidentally inflate the context
 * - It's explicit and self-documenting what's included
 *
 * ## Docker Build Context Reference
 *
 * The build context is the directory Docker uses as the root for COPY/ADD commands.
 * When you run: docker build -f Dockerfile /path/to/context
 * Docker sends the entire /path/to/context directory tree to the daemon.
 *
 * Example:
 * - If context is /project, then COPY pyproject.toml . copies /project/pyproject.toml
 * - If context is /tmp/minimal, then COPY pyproject.toml . copies /tmp/minimal/pyproject.toml
 *
 * The size of the build context directly affects:
 * - Upload time to Docker daemon
 * - Memory usage during build
 * - Build layer cache effectiveness (hash includes context)
 * - ECR push time (AWS CDK must build and push the image)
 */
export class BedrockAgentDockerImage extends Construct {
    readonly imageUri: string

    private static readonly CACHE_DIRS = new Set([
        '__pycache__',
        '.pytest_cache',
        '.mypy_cache',
        '.ruff_cache',
        '.coverage',
        'htmlcov',
        '.hypothesis',
        '.tox',
        'dist',
        'build',
        '*.egg-info',
    ]);

    constructor(scope: Construct, id: string, props: Props) {
        super(scope, id);
        const dockerPath = this.node.tryGetContext("BedrockDockerfilePath");
        const projectRoot = this.node.tryGetContext("ProjectRootPath");

        // Create minimal build context with only necessary files
        const buildContext = this.createMinimalBuildContext(projectRoot, dockerPath);

        const asset = new ecr_assets.DockerImageAsset(this, `${props.appName}-AppImage`, {
            directory: buildContext,
            file: 'Dockerfile',
            platform: Platform.LINUX_ARM64,
        });

        this.imageUri = asset.imageUri;
        new cdk.CfnOutput(this, 'ImageUri', {value: this.imageUri});
    }

    /**
     * Creates a minimal Docker build context by copying only necessary files to a temp directory.
     *
     * This prevents accidentally including large directories (node_modules, .git, etc.)
     * in the Docker build, which would:
     * 1. Slow down builds significantly
     * 2. Increase memory usage
     * 3. Increase ECR push time
     * 4. Make builds unpredictable as project grows
     *
     * @param projectRoot The root directory of the project
     * @param dockerPath The path to the Dockerfile
     * @returns Path to the temporary build context directory
     */
    private createMinimalBuildContext(projectRoot: string, dockerPath: string): string {
        // Create temp directory for build context
        const tempDir = fs.mkdtempSync(path.join('/tmp', 'cdk-docker-context-'));

        // Copy pyproject.toml from project root (workspace configuration)
        fs.copyFileSync(
            path.join(projectRoot, 'pyproject.toml'),
            path.join(tempDir, 'pyproject.toml')
        );

        // Copy packages directory structure (only what the Dockerfile needs)
        const packagesDir = path.join(projectRoot, 'packages');
        const tempPackagesDir = path.join(tempDir, 'packages');
        fs.mkdirSync(tempPackagesDir, {recursive: true});

        // Copy bedrock package (source code + config)
        this.copyPackage(
            path.join(packagesDir, 'bedrock'),
            path.join(tempPackagesDir, 'bedrock')
        );

        // Copy shared package (source code + config)
        this.copyPackage(
            path.join(packagesDir, 'shared'),
            path.join(tempPackagesDir, 'shared')
        );

        // Copy Dockerfile to temp context root (so it's at the expected location)
        fs.copyFileSync(dockerPath, path.join(tempDir, 'Dockerfile'));

        return tempDir;
    }

    /**
     * Copies a package (pyproject.toml + src/) to the build context.
     *
     * This preserves the minimal structure needed by the Dockerfile:
     * - pyproject.toml: Package configuration and dependencies
     * - src/: Source code that gets copied into the image
     *
     * Other files in the package directory (tests/, docs/, etc.) are NOT copied.
     *
     * @param srcDir Source package directory in the project
     * @param destDir Destination package directory in the build context
     */
    private copyPackage(srcDir: string, destDir: string): void {
        fs.mkdirSync(destDir, {recursive: true});

        // Copy pyproject.toml (package configuration)
        const srcPyproject = path.join(srcDir, 'pyproject.toml');
        if (fs.existsSync(srcPyproject)) {
            fs.copyFileSync(srcPyproject, path.join(destDir, 'pyproject.toml'));
        }

        // Copy src/ directory recursively (excluding cache files)
        const srcSrcDir = path.join(srcDir, 'src');
        const destSrcDir = path.join(destDir, 'src');
        if (fs.existsSync(srcSrcDir)) {
            this.copyDirRecursive(srcSrcDir, destSrcDir);
        }
    }

    /**
     * Recursively copies a directory tree, excluding known build cache directories.
     *
     * Cache directories excluded (defined in CACHE_DIRS):
     * - __pycache__/: Python bytecode cache
     * - .pytest_cache/: Pytest cache
     * - .mypy_cache/: MyPy type checking cache
     * - .ruff_cache/: Ruff linter cache
     * - build/, dist/: Build artifacts
     * - And others
     *
     * By excluding these, we ensure the build context stays minimal even if
     * developers have run builds or tests locally.
     *
     * @param src Source directory to copy from
     * @param dest Destination directory to copy to
     */
    private copyDirRecursive(src: string, dest: string): void {
        fs.mkdirSync(dest, {recursive: true});

        const files = fs.readdirSync(src);
        for (const file of files) {
            // Skip cache directories - they're not needed in the Docker image
            // and can be very large (especially __pycache__)
            if (BedrockAgentDockerImage.CACHE_DIRS.has(file)) {
                continue;
            }

            const srcFile = path.join(src, file);
            const destFile = path.join(dest, file);

            if (fs.statSync(srcFile).isDirectory()) {
                this.copyDirRecursive(srcFile, destFile);
            } else {
                fs.copyFileSync(srcFile, destFile);
            }
        }
    }
}
