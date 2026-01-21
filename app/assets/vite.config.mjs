import { defineConfig } from 'vite';
import { viteStaticCopy } from 'vite-plugin-static-copy';
import path from 'path';


export default defineConfig({
  root: 'src',
  build: {
    outDir: '../../static',
    emptyOutDir: false,
    assetsDir: '',
    rollupOptions: {
      input: {
        codemirror: path.resolve(__dirname, 'src/js/codemirror.js'),
        core: path.resolve(__dirname, 'src/css/core.css'),
        sidebar: path.resolve(__dirname, 'src/css/sidebar.css'),
        timeline: path.resolve(__dirname, 'src/css/timeline.css'),
      },
      output: [
        {
          entryFileNames: chunk =>
            chunk.name === 'codemirror'
              ? 'js/vendor/codemirror.js'
              : 'js/[name].js',
          assetFileNames: ({ name }) => {
            if (/\.css$/.test(name)) return 'css/[name][extname]'
            if (/\.(woff|woff2|ttf|eot)$/.test(name)) return 'fonts/[name][extname]'
            if (/\.(png|jpg|jpeg|svg|gif)$/.test(name)) return 'images/[name][extname]'
            return '[name][extname]'
          },
        },
      ],
    },
    minify: 'esbuild',
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
      '@js': path.resolve(__dirname, 'src/js'),
      '@css': path.resolve(__dirname, 'src/css'),
      '@fonts': path.resolve(__dirname, 'src/fonts'),
    },
  },
  plugins: [
    viteStaticCopy({
      targets: [
        // JavaScript
        {
          src: path.resolve(__dirname, 'node_modules/chart.js/dist/chart.umd.min.js'),
          dest: 'js/vendor',
        },
        {
          src: path.resolve(__dirname, 'node_modules/flatpickr/dist/flatpickr.min.js'),
          dest: 'js/vendor/calendar',
        },
        {
          src: path.resolve(__dirname, 'node_modules/flatpickr/dist/plugins/monthSelect/index.js'),
          dest: 'js/vendor/calendar',
          rename: 'flatpickr-monthSelect.js',
        },
        {
          src: path.resolve(__dirname, 'node_modules/fullcalendar/index.global.min.js'),
          dest: 'js/vendor/calendar',
          rename: 'fullcalendar.global.min.js',
        },
        {
          src: path.resolve(__dirname, 'node_modules/handlebars/dist/handlebars.min.js'),
          dest: 'js/vendor',
        },
        {
          src: path.resolve(__dirname, 'node_modules/sortablejs/Sortable.min.js'),
          dest: 'js/vendor',
        },
        {
          src: path.resolve(__dirname, 'node_modules/markdown-it/dist/markdown-it.min.js'),
          dest: 'js/vendor',
        },
        {
          src: path.resolve(__dirname, 'node_modules/@knight-lab/timelinejs/dist/js/timeline.js'),
          dest: 'js/vendor',
          rename: 'timelinejs.js',
        },
        {
          src: path.resolve(__dirname, 'node_modules/@knight-lab/timelinejs/dist/js/timeline.js.map'),
          dest: 'js/vendor',
        },
        {
          src: path.resolve(__dirname, 'node_modules/bootstrap/dist/js/bootstrap.min.js'),
          dest: 'js/vendor',
        },
        {
          src: path.resolve(__dirname, 'node_modules/bootstrap/dist/js/bootstrap.min.js.map'),
          dest: 'js/vendor',
        },
        {
          src: path.resolve(__dirname, 'node_modules/jquery/dist/jquery.min.js'),
          dest: 'js/vendor',
        },
        {
          src: path.resolve(__dirname, 'node_modules/jquery-ui/dist/jquery-ui.min.js'),
          dest: 'js/vendor',
        },
        {
          src: path.resolve(__dirname, 'node_modules/select2/dist/js/select2.min.js'),
          dest: 'js/vendor',
        },
        {
          src: path.resolve(__dirname, 'node_modules/zxcvbn/dist/zxcvbn.js'),
          dest: 'js/vendor',
        },
        {
          src: path.resolve(__dirname, 'node_modules/vue/dist/vue.global.js'),
          dest: 'js/vendor',
        },
        {
          src: path.resolve(__dirname, 'node_modules/@popperjs/core/dist/umd/popper.min.js'),
          dest: 'js/vendor',
        },
        {
          src: path.resolve(__dirname, 'node_modules/@popperjs/core/dist/umd/popper.min.js.map'),
          dest: 'js/vendor',
        },
        // Day.js
        {
          src: path.resolve(__dirname, 'node_modules/dayjs/dayjs.min.js'),
          dest: 'js/vendor/dayjs',
        },
        {
          src: path.resolve(__dirname, 'node_modules/dayjs/plugin/utc.js'),
          dest: 'js/vendor/dayjs',
          rename: 'dayjs-utc.js',
        },
        {
          src: path.resolve(__dirname, 'node_modules/dayjs/plugin/relativeTime.js'),
          dest: 'js/vendor/dayjs',
          rename: 'dayjs-relativeTime.js',
        },
        // CSS
        {
          src: path.resolve(__dirname, 'node_modules/flatpickr/dist/flatpickr.min.css'),
          dest: 'css/vendor/calendar',
        },
        {
          src: path.resolve(__dirname, 'node_modules/flatpickr/dist/plugins/monthSelect/style.css'),
          dest: 'css/vendor/calendar',
          rename: 'flatpickr-monthSelect.css',
        },
        {
          src: path.resolve(__dirname, 'node_modules/bootstrap/dist/css/bootstrap.min.css'),
          dest: 'css/vendor/',
        },
        {
          src: path.resolve(__dirname, 'node_modules/bootstrap/dist/css/bootstrap.min.css.map'),
          dest: 'css/vendor/',
        },
        {
          src: path.resolve(__dirname, 'node_modules/jquery-ui/dist/themes/base/jquery-ui.min.css'),
          dest: 'css/vendor/',
        },
        {
          src: path.resolve(__dirname, 'node_modules/select2/dist/css/select2.min.css'),
          dest: 'css/vendor/',
        },
        {
          src: path.resolve(__dirname, 'node_modules/@knight-lab/timelinejs/dist/css/timeline.css'),
          dest: 'css/vendor/',
          rename: 'timelinejs.css',
        },
        {
          src: path.resolve(__dirname, 'node_modules/@knight-lab/timelinejs/dist/css/timeline.css.map'),
          dest: 'css/vendor/',
          rename: 'timelinejs.css.map'
        },
        {
          src: path.resolve(__dirname, 'node_modules/select2-bootstrap-5-theme/dist/select2-bootstrap-5-theme.min.css'),
          dest: 'css/vendor/',
        },
        // FontAwesome CSS with URL transformation
        {
          src: path.resolve(__dirname, 'node_modules/@fortawesome/fontawesome-free/css/all.min.css'),
          dest: 'css/vendor',
          rename: 'fontawesome.css',
          transform: (content) => {
            return content.replace(
              /url\(['"]?\.\.\/webfonts\/([^'"]+)['"]?\)/g,
              `url('../../fonts/vendor/$1')`
            );
          },
        },
        // FontAwesome Fonts
        {
          src: path.resolve(__dirname, 'node_modules/@fortawesome/fontawesome-free/webfonts/fa-{brands,solid}-*.{ttf,woff2}'),
          dest: 'fonts/vendor',
        },
      ],
    }),
  ],
});
