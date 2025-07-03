const fs = require('fs');
const path = require('path');

function copy(src, dest) {
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  fs.copyFileSync(src, dest);
}

function main() {
  const paths = [
    [
      'node_modules/bootstrap/dist/css/bootstrap.min.css',
      'static/vendor/bootstrap.min.css'
    ],
    [
      'node_modules/bootstrap/dist/js/bootstrap.bundle.min.js',
      'static/vendor/bootstrap.bundle.min.js'
    ],
    [
      'node_modules/plotly.js-dist-min/plotly.min.js',
      'static/vendor/plotly.min.js'
    ],
  ];

  for (const [src, dest] of paths) {
    if (fs.existsSync(src)) {
      copy(src, dest);
      console.log(`Copied ${src} -> ${dest}`);
    } else {
      console.warn(`Missing ${src}, did you run \`npm install\`?`);
    }
  }
}

if (require.main === module) {
  main();
}
