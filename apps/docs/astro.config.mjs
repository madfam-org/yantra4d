// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import { unified } from '@astrojs/markdown-remark';

// https://astro.build/config
export default defineConfig({
	// Astro 7 defaults to the Sätteri Markdown processor, which renders `--` as an
	// en dash. These pages use `--` for an em dash, so keep the remark pipeline
	// (the upgrade guide's supported opt-out) until the sources are converted.
	markdown: {
		processor: unified(),
	},
	integrations: [
		starlight({
			title: '4D Docs',
			logo: {
				src: './public/logo.svg',
			},
			customCss: [
				'./src/styles/custom.css'
			],
			social: [
				{ icon: 'github', label: 'GitHub', href: 'https://github.com/madfam-org/yantra4d' }
			],
			sidebar: [
				{
					label: 'Overview',
					items: [{ autogenerate: { directory: 'overview' } }],
				},
				{
					label: 'Platform',
					items: [{ autogenerate: { directory: 'platform' } }],
				},
				{
					label: 'Hyperobjects Commons',
					items: [{ autogenerate: { directory: 'commons' } }],
				},
				{
					label: 'Developer API',
					items: [{ autogenerate: { directory: 'developer' } }],
				},
			],
		}),
	],
});
