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
      '@dummy': path.resolve(__dirname, 'src/api/_data_/dummy'),
      '@docs': path.resolve(__dirname, 'src/api/_data_/docs'),
      '@hooks' : path.resolve(__dirname, 'src/hooks'),
      '@utils' : path.resolve(__dirname, 'src/utils')

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
  jest: {
    configure: (jestConfig) => {
      jestConfig.moduleNameMapper = {
        '^@components(.*)$': '<rootDir>/src/components$1',
        '^@pages(.*)$': '<rootDir>/src/pages$1',
        '^@core(.*)$': '<rootDir>/src/components/core$1',
        '^@login(.*)$': '<rootDir>/src/components/Login$1',
        '^@utils(.*)$': '<rootDir>/src/utils$1',
        '^@hooks(.*)$': '<rootDir>/src/hooks$1',
        '^@context(.*)$': '<rootDir>/src/context$1',
        '^@assets(.*)$': '<rootDir>/src/assets$1',
        '^@services(.*)$': '<rootDir>/src/services$1',
        '^@auth(.*)$': '<rootDir>/src/services/auth$1',
        '^@api(.*)$': '<rootDir>/src/api$1',
        '^@dummy(.*)$': '<rootDir>/src/api/_data_/dummy$1',
        '^@docs(.*)$': '<rootDir>/src/api/_data_/docs$1',
      };
      // Přidáme transformIgnorePatterns pro date-fns a react-datepicker
      jestConfig.transformIgnorePatterns = [
        '/node_modules/(?!date-fns|react-datepicker)/',
      ];
      jestConfig.roots = [
        '<rootDir>/src',
        '<rootDir>/__mocks__', // Přidáme tuto cestu
      ];
      return jestConfig;
    },
  },
  eslint: {
    enable: false,
  },
};