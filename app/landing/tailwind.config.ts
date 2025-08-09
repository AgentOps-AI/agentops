import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    container: {
      center: true,
      padding: '2rem',
      screens: {
        '2xl': '1400px',
      },
    },
    extend: {
      backgroundSize: {
        '50%': '50%',
        '75%': '75%',
        '100%': '100%',
      },
      backgroundImage: {
        'purple-button': `
          url('/static-only.png'),
          linear-gradient(to right, #6E43DC, #8051F9)
        `,
        'purple-button-hover': `
          url('/static-only.png'),
          linear-gradient(to right, #8864E2, #9E7AFA)
        `,
        'primary-button': `
          url('/static-only.png'),
          linear-gradient(to right, #141B34, #303C67)
        `,
        'primary-button-hover': `
          url('/static-only.png'),
          linear-gradient(to right, #1E284D, #3E4D84)
        `,
      },
      fontFamily: {
        jetbrains: ['JetBrains Mono', 'monospace'],
      },
      boxShadow: {
        'purple-button': `
          inset 0 0 6px 2px rgba(255, 255, 255, 0.16), 
          inset 0 -2px 0px 0 rgba(0, 0, 0, 0.25), 
          inset 0 2px 0px 0 rgba(255, 255, 255, 0.25),
          0 50px 127px 0 rgba(110, 67, 220, 0.2),
          0 42px 53px 0 rgba(110, 67, 220, 0.3),
          0 22px 28px 0 rgba(110, 67, 220, 0.2),
          0 12px 16px 0 rgba(110, 67, 220, 0.2),
          0 6px 8px 0 rgba(110, 67, 220, 0.2),
          0 3px 3.5px 0 rgba(110, 67, 220, 0.2)`,
        'primary-button': ` 
          inset 0 0 2px 1px rgba(255, 255, 255, 0.2), 
          inset 0 -2px 0px 0 rgba(0, 0, 0, 0.31), 
          inset 0 2px 0px 0 rgba(255, 255, 255, 0.25),
          0 50px 127px 0 rgba(48, 60, 103, 0.4),
          0 42px 53px 0 rgba(48, 60, 103, 0.2),
          0 22px 28px 0 rgba(48, 60, 103, 0.2),
          0 12px 16px 0 rgba(48, 60, 103, 0.2),
          0 6px 8px 0 rgba(48, 60, 103, 0.2),
          0 3px 3.5px 0 rgba(48, 60, 103, 0.3)`,
      },
      colors: {
        'blue-start': '#141B34',
        'blue-end': '#303C67',
        'purple-start': '#6E43DC',
        'purple-end': '#8051F9',
        'card-background': '#F1F2FD',
      },
    },
  },
  plugins: [],
};
export default config;
