const path = require('path');

module.exports = {
  content: [path.resolve(__dirname, '../../public/liturgia-cnbb.html')],
  theme: {
    extend: {
      colors: {
        liturgia: {
          vinho: '#6b2635',
          papel: '#f7f5f0',
          ouro: '#bd9955',
          tinta: '#292524',
        },
      },
    },
  },
  plugins: [],
};
