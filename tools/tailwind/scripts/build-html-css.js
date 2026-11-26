const fs = require('fs').promises;
const path = require('path');
const postcss = require('postcss');
const tailwindcss = require('tailwindcss');
const tailwindConfig = require('../tailwind.config.cjs');

const root = path.resolve(__dirname, '../../..');
const inputPath = path.join(__dirname, '../input.css');
const htmlPath = path.join(root, 'public/liturgia-cnbb.html');
const generatedStyle = /<style id="tailwind-generated">[\s\S]*?<\/style>/;

async function buildHtmlCss() {
  const [input, html] = await Promise.all([
    fs.readFile(inputPath, 'utf8'),
    fs.readFile(htmlPath, 'utf8'),
  ]);
  const result = await postcss([tailwindcss(tailwindConfig)]).process(input, {
    from: inputPath,
  });

  if (!generatedStyle.test(html)) {
    throw new Error('O marcador de CSS do Tailwind não foi encontrado no HTML.');
  }

  const updatedHtml = html.replace(
    generatedStyle,
    `<style id="tailwind-generated">\n${result.css}\n</style>`,
  );
  await fs.writeFile(htmlPath, updatedHtml);
}

buildHtmlCss().catch(error => {
  console.error('Falha ao compilar o CSS do visualizador:', error);
  process.exitCode = 1;
});
