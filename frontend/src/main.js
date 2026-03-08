import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import 'vuetify/styles'
import '@mdi/font/css/materialdesignicons.css'
import App from './App.vue'

const vuetify = createVuetify({
  components,
  directives,
  theme: {
    defaultTheme: 'dark',
    themes: {
      dark: {
        colors: {
          primary: '#00E5FF',
          secondary: '#FF6B35',
          background: '#0D1117',
          surface: '#161B22',
          'surface-variant': '#21262D',
          error: '#FF4444',
          warning: '#FFB800',
          success: '#3FB950',
          info: '#58A6FF',
          'on-background': '#E6EDF3',
          'on-surface': '#E6EDF3',
          'on-surface-variant': '#C9D1D9',
        },
      },
    },
  },
})

const pinia = createPinia()
const app = createApp(App)
app.use(pinia)
app.use(vuetify)
app.mount('#app')
