# External Images Directory

## Purpose
This directory serves as a centralized repository for images that are used not only within our documentation but also embedded in external websites via direct links. 

## Automatic Synchronization
Any updates made to the images in this directory (such as replacing an image file with a new version) will be reflected across all external sites that display these images. This is because the image URLs remain constant, and the external sites dynamically fetch the latest version of the image from this directory.

To create a URL that consistenly updates, use the pattern:
```
https://raw.githubusercontent.com/AgentOps-AI/agentops/main/docs/images/external/<filename>.<extension>
```

## Usage Guidelines
- **Updating Images**: To update an image, upload the new file with the exact same name as the one it's replacing. This ensures that the image update is seamless across all platforms.
- **Consistency**: Regularly check that the images are up-to-date and accurately represent our brand and documentation standards.
- **Do Not Remove**: Avoid deleting images from this directory. Removal of images can lead to broken links and missing visuals on external sites that rely on these images.

## Example
If you update the `logo.png` file in this directory, the new logo will automatically appear in place of the old one on all external documentation pages that link to this image.

**Important**: Deletions and modifications can have immediate and widespread effects. Always verify that changes made here are intentional and correct before proceeding.