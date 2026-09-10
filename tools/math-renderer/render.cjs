// Local TeX-to-SVG entry point. No browser, network requests or dynamic TeX loading.
const {mathjax} = require('mathjax-full/js/mathjax.js');
const {TeX} = require('mathjax-full/js/input/tex.js');
const {SVG} = require('mathjax-full/js/output/svg.js');
const {liteAdaptor} = require('mathjax-full/js/adaptors/liteAdaptor.js');
const {RegisterHTMLHandler} = require('mathjax-full/js/handlers/html.js');
require('mathjax-full/js/input/tex/ams/AmsConfiguration.js');
require('mathjax-full/js/input/tex/newcommand/NewcommandConfiguration.js');
require('mathjax-full/js/input/tex/configmacros/ConfigMacrosConfiguration.js');
const adaptor = liteAdaptor();
RegisterHTMLHandler(adaptor);
const doc = mathjax.document('', {
  InputJax: new TeX({packages: ['base', 'ams', 'newcommand', 'configmacros'], maxBuffer: 20000}),
  OutputJax: new SVG({fontCache: 'none'})
});
const input = require('fs').readFileSync(0, 'utf8');
const node = doc.convert(input, {display: true});
let svg = adaptor.outerHTML(adaptor.firstChild(node));
if (svg.includes('data-mml-node="merror"')) throw new Error('Ungültige LaTeX-Formel');
svg = svg.replace(/(width|height)="([\d.]+)ex"/g, (_, key, size) => `${key}="${Number(size)*16}px"`);
process.stdout.write(svg);
