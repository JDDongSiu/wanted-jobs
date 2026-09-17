import { resolve } from 'node:path'

import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  base: "/wanted-jobs/",
  build: {
    // 프론트엔드 공고와 보건관리자 공고를 각각 다른 주소로 띄운다.
    // hse/index.html 은 dist/hse/index.html 로 나가 /wanted-jobs/hse/ 가 된다.
    rollupOptions: {
      input: {
        main: resolve(import.meta.dirname, 'index.html'),
        hse: resolve(import.meta.dirname, 'hse/index.html'),
      },
    },
  },
})
