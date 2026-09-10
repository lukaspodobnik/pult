# Lokaler Formelrenderer

`render.cjs` liest LaTeX von stdin und schreibt SVG nach stdout. Das eingecheckte
Bundle unter `src/pult/assets/math-renderer.cjs` wird mit dem Python-Paket ausgeliefert.
Zur Laufzeit genügt Node.js; npm und dieser Werkzeugordner sind nicht erforderlich.

Reproduzierbar neu bauen:

```sh
npm ci --prefix tools/math-renderer
npm run build --prefix tools/math-renderer
```

MathJax 3.2.2, TeX-Schrift (Computer-Modern-basiert), Apache-2.0.
Die verwendeten Module stehen im Bundle mit ihren ursprünglichen Quellpfaden.
Die Lizenz liegt unter `src/pult/legal/MathJax-Apache-2.0.txt`.
Es werden ausschließlich die TeX-Pakete base, ams, newcommand und configmacros
verwendet; kein dynamisches Laden von Erweiterungen oder externen Ressourcen.
