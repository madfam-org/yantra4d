/**
 * The e2e web server: `astro preview` of `dist/` on 127.0.0.1:4321, started
 * through Astro's JS API instead of the CLI.
 *
 * Same server, same dist, same host and port as `npm run preview -- --host
 * 127.0.0.1 --port 4321`. The difference is who owns the process: since Astro
 * 7 the CLI detects an agent shell (Claude Code, Cursor, Codex, Gemini CLI —
 * `am-i-vibing`) and detaches the preview into a background daemon, so under
 * one of those the `npm run preview` process exits the moment the daemon is
 * up, Playwright's webServer reports "Process from config.webServer exited
 * early", and a stray daemon keeps the port. The API has no such behaviour:
 * the server lives and dies with this process, which Playwright owns.
 *
 * Run `npm run build` first; this serves whatever is in dist/.
 */
/* global process */
import { preview } from 'astro';

const host = process.env.LANDING_E2E_HOST || '127.0.0.1';
const port = Number(process.env.LANDING_E2E_PORT || 4321);

const server = await preview({ server: { host, port }, logLevel: 'info' });

const stop = async () => {
  await server.stop();
  process.exit(0);
};
process.once('SIGTERM', stop);
process.once('SIGINT', stop);
