/* Apply saved appearance before paint. */
try{document.documentElement.dataset.theme=localStorage.getItem('qyad-theme')||'light';document.documentElement.dataset.sidebar=localStorage.getItem('qyad-sidebar')||'expanded';}catch(e){}
