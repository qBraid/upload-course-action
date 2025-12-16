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
 * Initialize GCS client with qBraid API key
 */
function initializeGCSClient(apiKey) {
  // The API key is used as credentials
  // For GCS, we need to create a temporary credentials object
  // This assumes the API key is a service account key in JSON format
  try {
    const credentials = JSON.parse(apiKey);
    return new Storage({ credentials });
  } catch (error) {
    // If API key is not JSON, treat it as an authentication token
    core.warning('API key is not in JSON format. Using as authentication token.');
    // For simple API key authentication, we might need to use it differently
    // depending on how qBraid has set up their GCS authentication
    return new Storage({
      apiKey: apiKey
    });
  }
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
      
      // Construct destination path in bucket
      let destinationFile = relativePath;
      if (destinationPath) {
        destinationFile = path.join(destinationPath, relativePath).replace(/\\/g, '/');
      }

      core.info(`Uploading: ${relativePath} -> ${destinationFile}`);

      await bucket.upload(filePath, {
        destination: destinationFile,
        metadata: {
          cacheControl: 'public, max-age=3600',
        },
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
    // Get inputs
    const bucketName = core.getInput('bucket-name', { required: true });
    const apiKey = core.getInput('api-key', { required: true });
    const sourcePath = core.getInput('source-path') || '.';
    const destinationPath = core.getInput('destination-path') || '';
    const excludePatternsString = core.getInput('exclude-patterns');

    core.info('Starting upload to GCS...');
    core.info(`Bucket: ${bucketName}`);
    core.info(`Source: ${sourcePath}`);
    core.info(`Destination: ${destinationPath || '(root)'}`);

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

    // Initialize GCS client
    const storage = initializeGCSClient(apiKey);

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
    
    const uploadUrl = `https://storage.googleapis.com/${bucketName}/${destinationPath}`;
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
