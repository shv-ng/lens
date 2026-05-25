import adapter from '@sveltejs/adapter-static';

const config = {
    compilerOptions: {
        runes: ({ filename }) => (filename.split(/[/\\]/).includes('node_modules') ? undefined : true)
    },
    kit: {
        adapter: adapter({
            pages: 'build',
            assets: 'build',
            fallback: 'index.html',   // SPA fallback — nginx serves this for all routes
            precompress: false
        })
    }
};

export default config;
