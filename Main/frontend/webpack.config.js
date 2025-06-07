const path = require('path');
const CopyPlugin = require('copy-webpack-plugin');
const webpack = require('webpack');

module.exports = {
    entry: './src/main.js',
    mode: 'production',
    output: {
        filename: '[name].js',
        path: path.resolve(__dirname, 'dist'),
    },
    devtool: false,  // Disable source maps to avoid encoding issues
    module: {
        rules: [
            {
                test: /\.js$/,
                exclude: /node_modules/,
                use: {
                    loader: 'babel-loader',
                },
            },
            {
                test: /\.css$/,
                use: [
                    'style-loader',
                    {
                        loader: 'css-loader',
                        options: {
                            url: false // Disable processing of font URLs
                        }
                    }
                ],
            },
            {
                test: /\.(woff|woff2|ttf|eot)$/,
                type: 'asset/inline',
                generator: {
                    dataUrl: () => '', // Return empty string for fonts
                },
            },
        ],
    },
    resolve: {
        extensions: ['.js'],
    },
    optimization: {
        splitChunks: {
            chunks: 'all',
            cacheGroups: {
                vendor: {
                    test: /[\\/]node_modules[\\/](?!katex)/,
                    name: 'vendors',
                    priority: 10
                },
                katex: {
                    test: /[\\/]node_modules[\\/]katex[\\/]/,
                    name: 'katex',
                    priority: 20,
                    enforce: true
                }
            }
        }
    },
    performance: {
        hints: "warning"
    },
    plugins: [
        new webpack.BannerPlugin({
            banner: '// @charset "UTF-8";',
            raw: true
        }),
        // Custom plugin to ensure UTF-8 encoding
        {
            apply: (compiler) => {
                compiler.hooks.emit.tapAsync('EnsureUTF8Plugin', (compilation, callback) => {
                    Object.keys(compilation.assets).forEach((filename) => {
                        if (filename === 'katex.js') {
                            const source = compilation.assets[filename].source();
                            // Remove any non-UTF-8 characters and ensure proper encoding
                            const cleanSource = source.replace(/[^\x00-\x7F]/g, (char) => {
                                return '\\u' + ('0000' + char.charCodeAt(0).toString(16)).slice(-4);
                            });
                            compilation.assets[filename] = {
                                source: () => cleanSource,
                                size: () => cleanSource.length
                            };
                        }
                    });
                    callback();
                });
            }
        },
        new CopyPlugin({
          patterns: [
            { from: 'src/manifest.json', to: '.' },
            { from: 'src/assets/', to: 'assets/' },
          ],
        }),
      ],
};
