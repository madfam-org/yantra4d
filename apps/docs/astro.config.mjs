// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

// https://astro.build/config
export default defineConfig({
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
					autogenerate: { directory: 'overview' },
				},
				{
					label: 'Platform',
					autogenerate: { directory: 'platform' },
				},
				{
					label: 'Hyperobjects Commons',
					autogenerate: { directory: 'commons' },
				},
				{
					label: 'Developer API',
					autogenerate: { directory: 'developer' },
				},
			],
		}),
	],
});
