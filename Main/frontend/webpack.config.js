const path = require('path');
const CopyPlugin = require('copy-webpack-plugin');

module.exports = {
    entry: './src/main.js',
    mode: 'production',
    output: {
        filename: 'bundle.js',
        path: path.resolve(__dirname, 'dist'),
    },
    devtool: 'source-map',  // CSP compliance
    module: {
        rules: [
            {
                test: /\.js$/,
                exclude: /node_modules/,
                use: {
                    loader: 'babel-loader',
                },
            },
        ],
    },
    resolve: {
        extensions: ['.js'],
    },
    plugins: [
        new CopyPlugin({
          patterns: [
            { from: 'src/manifest.json', to: '.' },
            { from: 'src/textbox.css', to: '.' },
            { from: 'src/assets/', to: 'assets/' },
            // Add other assets here if needed (icons, etc.)
          ],
        }),
      ],
};
