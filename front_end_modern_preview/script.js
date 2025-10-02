(function () {
  const html = document.documentElement;
  const themeToggle = document.getElementById('themeToggle');
  const protocolInput = document.getElementById('protocolFile');
  const crfInput = document.getElementById('crfFile');
  const protocolDrop = document.getElementById('protocolDropzone');
  const crfDrop = document.getElementById('crfDropzone');
  const generateButton = document.getElementById('generateButton');
  const progressContainer = document.getElementById('progressContainer');
  const progressBar = document.getElementById('progressBar');
  const progressLabel = document.getElementById('progressLabel');
  const outputSection = document.getElementById('outputSection');
  const downloadLink = document.getElementById('downloadLink');

  // Theme
  const savedTheme = localStorage.getItem('theme');
  if (savedTheme) html.setAttribute('data-theme', savedTheme);
  updateThemeIcon();

  themeToggle?.addEventListener('click', () => {
    const current = html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-theme', current);
    localStorage.setItem('theme', current);
    updateThemeIcon();
  });

  function updateThemeIcon() {
    const isDark = html.getAttribute('data-theme') === 'dark';
    const icon = themeToggle?.querySelector('.button-icon');
    if (icon) icon.textContent = isDark ? '☀️' : '🌙';
  }

  // Dropzones
  setupDropzone(protocolDrop, protocolInput);
  setupDropzone(crfDrop, crfInput);

  // Browse buttons
  document.querySelectorAll('.browse-button').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      const id = btn.getAttribute('data-input');
      const input = document.getElementById(id);
      input?.click();
    });
  });

  // Enable generate when both files are present
  function refreshGenerateState() {
    const ready = Boolean(protocolInput.files[0]) && Boolean(crfInput.files[0]);
    generateButton.disabled = !ready;
  }

  protocolInput.addEventListener('change', refreshGenerateState);
  crfInput.addEventListener('change', refreshGenerateState);

  // Generate flow with simulated progress
  generateButton.addEventListener('click', () => {
    progressContainer.classList.remove('hidden');
    outputSection.classList.add('hidden');
    generateButton.disabled = true;

    let p = 0;
    progressLabel.textContent = 'Processing…';
    const timer = setInterval(() => {
      p = Math.min(100, p + Math.floor(Math.random() * 18) + 6);
      progressBar.style.width = p + '%';
      if (p >= 100) {
        clearInterval(timer);
        progressLabel.textContent = 'Done';
        setTimeout(() => {
          outputSection.classList.remove('hidden');
          downloadLink.href = 'PTD_Template.xlsx';
          generateButton.disabled = false;
        }, 250);
      }
    }, 220);
  });

  function setupDropzone(zone, input) {
    if (!zone || !input) return;
    const setFile = (file) => {
      if (!file) return;
      const text = zone.querySelector('.dropzone-text');
      if (text) {
        const strong = text.querySelector('strong');
        if (strong) strong.textContent = file.name;
      }
      zone.classList.add('has-file');
      refreshGenerateState();
    };

    zone.addEventListener('click', () => input.click());
    zone.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        input.click();
      }
    });

    zone.addEventListener('dragenter', (e) => { e.preventDefault(); zone.classList.add('dragover'); });
    zone.addEventListener('dragover', (e) => { e.preventDefault(); zone.classList.add('dragover'); });
    zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
    zone.addEventListener('drop', (e) => {
      e.preventDefault();
      zone.classList.remove('dragover');
      if (e.dataTransfer?.files?.length) {
        input.files = e.dataTransfer.files;
        setFile(input.files[0]);
      }
    });

    input.addEventListener('change', () => setFile(input.files[0]));
  }
})();
