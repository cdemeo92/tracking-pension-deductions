# Tracker assets

This folder contains the source for the browser-based tracker. The HTML template provides the page shell; the TypeScript modules separate calculations, payslip parsing, page interactions, and Artifact persistence.

## Build

Run from the repository root:

```sh
npm run build
```

Vite generates `dist/template.html` as one standalone HTML file with local JavaScript and CSS inlined. PDF.js remains loaded from its CDN. The generated `dist/` directory is ignored by Git.

For a local development preview, run `npm run dev` from the repository root.

## Test

Run the frontend unit and UI tests without building first:

```sh
npm run test:frontend:unit
```

The generated-HTML test requires a prior build:

```sh
npm run build
npm run test:frontend:build
```

`npm run test:frontend` runs both frontend test groups. `npm test` runs the full project test pipeline.