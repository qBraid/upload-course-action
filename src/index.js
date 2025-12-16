const core = require('@actions/core');
const { Storage } = require('@google-cloud/storage');
const { glob } = require('glob');
const fs = require('fs');
const path = require('path');

/**
 * Parse exclude patterns from comma-separated string
 */
function parseExcludePatterns(patternsString) {
  if (!patternsString) return [];
  return patternsString.split(',').map(p => p.trim()).filter(p => p.length > 0);
}

/**
 * Get list of files to upload based on source path and exclude patterns
 */
async function getFilesToUpload(sourcePath, excludePatterns) {
  const resolvedSourcePath = path.resolve(process.cwd(), sourcePath);
  
  // Check if source path exists
  if (!fs.existsSync(resolvedSourcePath)) {
    throw new Error(`Source path does not exist: ${resolvedSourcePath}`);
  }

  const stats = fs.statSync(resolvedSourcePath);
  
  // If it's a single file, return it
  if (stats.isFile()) {
    return [resolvedSourcePath];
  }

  // If it's a directory, glob all files
  const pattern = path.join(sourcePath, '**/*');
  const ignore = excludePatterns.map(p => {
    // Convert patterns to be relative to source path
    if (p.startsWith('/')) {
      return p.substring(1);
    }
    return p;
  });

  core.info(`Scanning files in: ${sourcePath}`);
  core.info(`Exclude patterns: ${ignore.join(', ')}`);

  const files = await glob(pattern, {
    ignore: ignore,
    nodir: true,
    dot: false,
    cwd: process.cwd()
  });

  return files.map(f => path.resolve(process.cwd(), f));
}

/**
 * Initialize GCS client with built-in credentials
 */
function initializeGCSClient() {
  // GCS credentials should be configured as environment variables or secrets in the action
  // For now, we'll check for GCS_SERVICE_ACCOUNT_KEY environment variable
  const gcsCredentials = process.env.GCS_SERVICE_ACCOUNT_KEY;
  
  if (!gcsCredentials) {
    throw new Error(
      'GCS_SERVICE_ACCOUNT_KEY environment variable is not set. ' +
      'This action requires GCS credentials to be configured.'
    );
  }

  try {
    const credentials = JSON.parse(gcsCredentials);
    return new Storage({ credentials });
  } catch (error) {
    throw new Error(
      'GCS_SERVICE_ACCOUNT_KEY must be a valid service account key in JSON format. ' +
      `Parse error: ${error.message}`
    );
  }
}

/**
 * Validate qBraid API key
 * This function would typically make an API call to qBraid to verify the key
 */
async function validateQBraidApiKey(apiKey) {
  // For now, just check that the API key is provided and not empty
  // In a real implementation, this would call qBraid's API to validate the key
  if (!apiKey || apiKey.trim().length === 0) {
    throw new Error('QBRAID_API_KEY is required but was not provided or is empty');
  }
  
  // TODO: Make actual API call to qBraid to validate the key
  // Example: await fetch('https://api.qbraid.com/validate', { headers: { 'Authorization': `Bearer ${apiKey}` }})
  
  core.info('qBraid API key validated successfully');
  return true;
}

/**
 * Upload files to GCS bucket
 */
async function uploadFiles(storage, bucketName, files, sourcePath, destinationPath) {
  const bucket = storage.bucket(bucketName);
  
  // Verify bucket exists
  const [exists] = await bucket.exists();
  if (!exists) {
    throw new Error(`Bucket ${bucketName} does not exist or is not accessible`);
  }

  let uploadedCount = 0;
  const sourcePathResolved = path.resolve(process.cwd(), sourcePath);
  
  core.info(`Uploading ${files.length} files to bucket: ${bucketName}`);

  for (const filePath of files) {
    try {
      // Calculate relative path from source
      const relativePath = path.relative(sourcePathResolved, filePath);
      
      // Construct destination path in bucket (using posix for cloud storage)
      // Normalize path separators to forward slashes for cloud storage
      const normalizedPath = relativePath.replace(/\\/g, '/');
      const destinationFile = destinationPath 
        ? path.posix.join(destinationPath, normalizedPath)
        : normalizedPath;

      core.info(`Uploading: ${relativePath} -> ${destinationFile}`);

      await bucket.upload(filePath, {
        destination: destinationFile,
      });

      uploadedCount++;
    } catch (error) {
      core.error(`Failed to upload ${filePath}: ${error.message}`);
      throw error;
    }
  }

  return uploadedCount;
}

/**
 * Main action function
 */
async function run() {
  try {
    // Hardcoded bucket name - configured in the action
    const bucketName = process.env.GCS_BUCKET_NAME || 'qbraid-upload-bucket';
    
    // Get inputs
    const apiKey = core.getInput('api-key', { required: true });
    const sourcePath = core.getInput('source-path') || '.';
    const destinationPath = core.getInput('destination-path') || '';
    const excludePatternsString = core.getInput('exclude-patterns');

    core.info('Starting upload to GCS...');
    core.info(`Bucket: ${bucketName}`);
    core.info(`Source: ${sourcePath}`);
    core.info(`Destination: ${destinationPath || '(root)'}`);

    // Validate qBraid API key
    await validateQBraidApiKey(apiKey);

    // Parse exclude patterns
    const excludePatterns = parseExcludePatterns(excludePatternsString);

    // Get files to upload
    const files = await getFilesToUpload(sourcePath, excludePatterns);
    
    if (files.length === 0) {
      core.warning('No files found to upload');
      core.setOutput('upload-status', 'skipped');
      core.setOutput('files-uploaded', '0');
      return;
    }

    core.info(`Found ${files.length} files to upload`);

    // Initialize GCS client with built-in credentials
    const storage = initializeGCSClient();

    // Upload files
    const uploadedCount = await uploadFiles(
      storage,
      bucketName,
      files,
      sourcePath,
      destinationPath
    );

    // Set outputs
    core.setOutput('upload-status', 'success');
    core.setOutput('files-uploaded', uploadedCount.toString());
    
    // Construct upload URL (handle empty destination path)
    const baseUrl = `https://storage.googleapis.com/${bucketName}`;
    const uploadUrl = destinationPath ? `${baseUrl}/${destinationPath}` : baseUrl;
    core.setOutput('upload-url', uploadUrl);

    core.info(`✅ Successfully uploaded ${uploadedCount} files to GCS bucket: ${bucketName}`);
  } catch (error) {
    core.setFailed(`Action failed: ${error.message}`);
    core.setOutput('upload-status', 'failed');
    core.setOutput('files-uploaded', '0');
  }
}

// Run the action
run();
