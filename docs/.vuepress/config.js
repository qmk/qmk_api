module.exports = {
  title: 'QMK API Documentation',
  description: 'Information on keyboards and keymaps, and a compile service.',
  markdown: {
    lineNumbers: true
  },
  themeConfig: {
    displayAllHeaders: true,
    docsDir: 'docs',
    editLinks: true,
    editLinkText: 'Suggest an improvement to this page!',
    lastUpdated: 'Last Updated',
    logo: '/favicon.png',
    repo: 'qmk/qmk_api',
    repoLabel: 'Fork',
    nav: [
      { text: 'Home', link: '/' },
      { text: 'Chat', link: 'https://discord.gg/V5Trhu2' },
    ],
    sidebar: [
      '/',
      'api_docs',
      'development_environment',
      'development_overview',
      'error_log',
      'keyboard_api',
      'keyboard_support',
      'operations',
    ]
  },
}
