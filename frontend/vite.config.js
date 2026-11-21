import {defineConfig, loadEnv} from 'vite';
import {apiBase} from './src/api.js';

export default defineConfig(({command, mode}) => {
  const env = {...loadEnv(mode, process.cwd(), 'VITE_'), ...process.env};
  if (command === 'build') {
    apiBase(env.VITE_API_URL, true);
    if (Object.keys(env).some(key => key.startsWith('VITE_') && key !== 'VITE_API_URL')) {
      throw new Error('Only VITE_API_URL may be exposed in the frontend build. Keep secrets on the backend.');
    }
  }
  return {};
});
