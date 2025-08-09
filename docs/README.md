# AgentOps Documentation

This directory contains the documentation for AgentOps, including setup guides, API references, and integration examples.

## 📖 Documentation Structure

- **v2/** - Latest SDK documentation and guides
- **v1/** - Legacy SDK documentation  
- **v0/** - Historical documentation
- **backend-setup.md** - Complete guide for setting up and running backend services

## 🚀 Quick Links

- **[Backend Setup Guide](backend-setup.md)** - Instructions for running the app directory services
- **API Reference** - Available in the versioned directories
- **Integration Examples** - SDK integration examples and tutorials

### 👩‍💻 Development

Install the [Mintlify CLI](https://www.npmjs.com/package/mintlify) to preview the documentation changes locally. To install, use the following command

```
npm i -g mintlify
```

Run the following command at the root of your documentation (where mint.json is)

```
mintlify dev
```

### 😎 Publishing Changes

Changes will be deployed to production automatically after pushing to the default branch.

You can also preview changes using PRs, which generates a preview link of the docs.

#### Troubleshooting

- Mintlify dev isn't running - Run `mintlify install` it'll re-install dependencies.
- Page loads as a 404 - Make sure you are running in a folder with `mint.json`
