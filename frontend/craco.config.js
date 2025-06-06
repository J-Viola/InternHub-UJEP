const path = require('path');

module.exports = {
  webpack: {
    alias: {
      '@components': path.resolve(__dirname, 'src/components'),
      '@pages': path.resolve(__dirname, 'src/pages'),
      '@core': path.resolve(__dirname, 'src/components/core'),
      '@login': path.resolve(__dirname, 'src/components/Login'),
      '@utils': path.resolve(__dirname, 'src/utils'),
      '@hooks': path.resolve(__dirname, 'src/hooks'),
      '@context': path.resolve(__dirname, 'src/context'),
      '@assets': path.resolve(__dirname, 'src/assets'),
      '@services': path.resolve(__dirname, 'src/services'),
      '@auth': path.resolve(__dirname, 'src/services/auth'),
      '@api': path.resolve(__dirname, 'src/api'),

    },
    configure: (webpackConfig) => {
      webpackConfig.ignoreWarnings = [
        {
          module: /react-datepicker/,
          message: /Failed to parse source map/,
        },
      ];
      return webpackConfig;
    }
  },
  eslint: {
    enable: false,
  },
}; 