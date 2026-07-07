# Documentation

## 🌐 Documentation en ligne
- **[Docsify Documentation](https://jinsudai-docsify.hf.space/)** - Documentation technique complète

## 📝 Documentation Markdown avec schemas Mermaid

- **[Services/docsify/README.md](../Services/docsify/docs/README.md)** - README du service docsify

## 💻 Documentation en accès Local

Si les HuggingFace Spaces sont en pause ou indisponibles, vous pouvez accéder aux services localement:

### Documentation Docsify
```bash
cd Services/docsify
npm install -g docsify-cli docsify-mermaid
docsify serve docs --port 7860 --open
```
Ou avec Docker:
```bash
cd Services/docsify
docker build -t jinsudai-docs .
docker run -p 7860:7860 jinsudai-docs
```
Puis ouvrez: http://localhost:7860