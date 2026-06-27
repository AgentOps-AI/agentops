# AgentOps Documentation

This directory contains the official documentation for AgentOps, built with [Mintlify](https://mintlify.com).

## 📚 Documentation Structure

- **v2/** - Latest documentation version
  - `introduction.mdx` - Getting started with AgentOps
  - `quickstart.mdx` - Quick setup guide
  - `integrations/` - Integration guides
  - `usage/` - Usage examples and best practices
  - `concepts/` - Core concepts and architecture

- **Backend Setup Guide** - [backend-setup.md](./backend-setup.md) - Comprehensive guide for running the AgentOps backend services

## 👩‍💻 Development

### Prerequisites

Install the [Mintlify CLI](https://www.npmjs.com/package/mintlify):

```bash
npm i -g mintlify
```

### Running Locally

Run the following command at the root of the docs directory:

```bash
mintlify dev
```

The documentation will be available at `http://localhost:3000`.

### Building Documentation

To build the documentation for production:

```bash
mintlify build
```

## 📝 Writing Documentation

### File Format

- Use `.mdx` files for documentation pages
- MDX allows you to use React components within Markdown
- Follow the existing structure in the `v2/` directory

### Adding New Pages

1. Create a new `.mdx` file in the appropriate directory
2. Update `mint.json` to include the new page in navigation
3. Use frontmatter for page metadata:

```mdx
---
title: "Page Title"
description: "Page description"
---
```

### Components

Mintlify provides various components for enhanced documentation:

- Code blocks with syntax highlighting
- API reference components
- Tabs and accordions
- Cards and callouts

Refer to the [Mintlify documentation](https://mintlify.com/docs) for component usage.

## 🚀 Publishing Changes

Changes are automatically deployed when pushed to the main branch. Preview deployments are created for pull requests.

### Deployment Process

1. Create a feature branch for your changes
2. Make your documentation updates
3. Create a pull request
4. Preview link will be generated automatically
5. After review and merge, changes deploy to production

## 🔧 Troubleshooting

### Common Issues

- **Mintlify dev isn't running**: Run `mintlify install` to reinstall dependencies
- **Page loads as 404**: Ensure you're running in the directory containing `mint.json`
- **Build errors**: Check that all referenced files exist and MDX syntax is valid

### Getting Help

- Check the [Mintlify documentation](https://mintlify.com/docs)
- Review existing documentation examples in the `v2/` directory
- Open an issue in the AgentOps repository

## 📄 Additional Resources

- [Backend Setup Guide](./backend-setup.md) - Detailed instructions for running backend services
- [API Documentation](https://api.agentops.ai/docs) - Interactive API reference
- [AgentOps GitHub](https://github.com/AgentOps-AI/AgentOps) - Main repository
