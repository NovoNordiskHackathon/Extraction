(function () {
  const html = document.documentElement;
  const protocolInput = document.getElementById('protocolFile');
  const crfInput = document.getElementById('crfFile');
  const protocolDrop = document.getElementById('protocolDropzone');
  const crfDrop = document.getElementById('crfDropzone');
  const protocolChip = document.getElementById('protocolChip');
  const crfChip = document.getElementById('crfChip');
  const generateButton = document.getElementById('generateButton');
  const progressContainer = document.getElementById('progressContainer');
  const progressBar = document.getElementById('progressBar');
  const progressLabel = document.getElementById('progressLabel');
  const outputSection = document.getElementById('outputSection');
  const downloadLink = document.getElementById('downloadLink');
  const toastContainer = document.getElementById('toastContainer');

  // Theme & Accent state
  const mql = window.matchMedia('(prefers-color-scheme: dark)');
  const savedMode = localStorage.getItem('themeMode') || 'auto';
  const savedAccent = localStorage.getItem('accent') || 'violet';
  html.setAttribute('data-mode', savedMode);
  html.setAttribute('data-accent', savedAccent);
  applyThemeFromMode(savedMode);
  setSelectedThemeButton(savedMode);
  setSelectedAccent(savedAccent);

  // Theme segment buttons
  document.querySelectorAll('.theme-segment .seg').forEach((btn) => {
    btn.addEventListener('click', () => {
      const mode = btn.getAttribute('data-mode');
      if (!mode) return;
      html.setAttribute('data-mode', mode);
      localStorage.setItem('themeMode', mode);
      applyThemeFromMode(mode);
      setSelectedThemeButton(mode);
      showToast(`Theme: ${capitalize(mode)}`,'info');
    });
  });

  // Accent swatches
  document.querySelectorAll('.accent-swatches .swatch').forEach((sw) => {
    sw.addEventListener('click', () => {
      const accent = sw.getAttribute('data-accent') || 'violet';
      html.setAttribute('data-accent', accent);
      localStorage.setItem('accent', accent);
      setSelectedAccent(accent);
      showToast(`Accent: ${capitalize(accent)}`,'info');
    });
  });

  // React to system theme when in auto
  mql.addEventListener('change', () => {
    if ((localStorage.getItem('themeMode') || 'auto') === 'auto') {
      applyThemeFromMode('auto');
    }
  });

  function applyThemeFromMode(mode) {
    const dark = mode === 'auto' ? mql.matches : mode === 'dark';
    html.setAttribute('data-theme', dark ? 'dark' : 'light');
  }

  function setSelectedThemeButton(mode) {
    document.querySelectorAll('.theme-segment .seg').forEach((btn) => {
      const selected = btn.getAttribute('data-mode') === mode;
      btn.setAttribute('aria-selected', String(selected));
      btn.classList.toggle('active', selected);
    });
  }

  function setSelectedAccent(accent) {
    document.querySelectorAll('.accent-swatches .swatch').forEach((sw) => {
      const selected = sw.getAttribute('data-accent') === accent;
      sw.setAttribute('aria-checked', String(selected));
      sw.style.outline = selected ? '2px solid #fff' : 'none';
    });
  }

  // Dropzones with tilt + drag/drop
  setupDropzone(protocolDrop, protocolInput, protocolChip);
  setupDropzone(crfDrop, crfInput, crfChip);

  // Browse buttons
  document.querySelectorAll('.browse-button').forEach((btn) => {
    btn.addEventListener('click', () => {
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

  protocolInput.addEventListener('change', () => { updateChip(protocolChip, protocolInput); refreshGenerateState(); });
  crfInput.addEventListener('change', () => { updateChip(crfChip, crfInput); refreshGenerateState(); });

  // Generate flow with simulated progress + confetti + toasts
  generateButton.addEventListener('click', () => {
    showToast('Generating PTD…','info');
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
          confetti();
          showToast('PTD is ready','success');
        }, 250);
      }
    }, 220);
  });

  function setupDropzone(zone, input, chipRow) {
    if (!zone || !input) return;

    // tilt interaction
    zone.addEventListener('mousemove', (e) => {
      const rect = zone.getBoundingClientRect();
      const x = (e.clientX - rect.left) / rect.width - 0.5; // [-0.5, 0.5]
      const y = (e.clientY - rect.top) / rect.height - 0.5;
      zone.style.setProperty('--ry', `${x * 6}deg`);
      zone.style.setProperty('--rx', `${-y * 6}deg`);
    });
    zone.addEventListener('mouseleave', () => {
      zone.style.setProperty('--ry', '0deg');
      zone.style.setProperty('--rx', '0deg');
    });

    const setFile = (file) => {
      if (!file) return;
      const text = zone.querySelector('.dropzone-text');
      if (text) {
        const strong = text.querySelector('strong');
        if (strong) strong.textContent = file.name;
      }
      zone.classList.add('has-file');
      updateChip(chipRow, input);
      showToast(`${file.name} added`,'info');
    };

    zone.addEventListener('click', () => input.click());
    zone.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault(); input.click();
      }
    });

    zone.addEventListener('dragenter', (e) => { e.preventDefault(); zone.classList.add('dragover'); });
    zone.addEventListener('dragover', (e) => { e.preventDefault(); zone.classList.add('dragover'); });
    zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
    zone.addEventListener('drop', (e) => {
      e.preventDefault(); zone.classList.remove('dragover');
      if (e.dataTransfer?.files?.length) {
        input.files = e.dataTransfer.files; setFile(input.files[0]); refreshGenerateState();
      }
    });

    input.addEventListener('change', () => { setFile(input.files[0]); refreshGenerateState(); });
  }

  function updateChip(container, input) {
    if (!container) return;
    container.innerHTML = '';
    const file = input.files?.[0];
    if (!file) return;
    const chip = document.createElement('div');
    chip.className = 'chip';
    chip.innerHTML = `<span class="chip-name">${file.name}</span><button class="chip-remove" aria-label="Remove">×</button>`;
    chip.querySelector('.chip-remove').addEventListener('click', () => {
      input.value = '';
      const dz = input.parentElement;
      if (dz?.classList?.contains('dropzone')) {
        dz.classList.remove('has-file');
        const strong = dz.querySelector('strong');
        if (strong) strong.textContent = dz.getAttribute('aria-label')?.replace('Upload ', '') || 'Document';
      }
      container.innerHTML = '';
      refreshGenerateState();
      showToast('File removed','info');
    });
    container.appendChild(chip);
  }

  function confetti() {
    const colors = ['#fde047','#f43f5e','#22c55e','#60a5fa','#a78bfa','#f59e0b'];
    const layer = document.createElement('div');
    layer.className = 'confetti';
    document.body.appendChild(layer);
    const count = 36;
    for (let i = 0; i < count; i++) {
      const piece = document.createElement('div');
      piece.className = 'confetti-piece';
      piece.style.left = Math.random()*100 + 'vw';
      piece.style.top = (-Math.random()*20) + 'vh';
      piece.style.background = colors[i % colors.length];
      const dur = 1200 + Math.random()*800;
      piece.style.animationDuration = dur + 'ms';
      piece.style.transform = `translateY(0) rotate(${Math.random()*360}deg)`;
      layer.appendChild(piece);
      setTimeout(() => piece.remove(), dur + 200);
    }
    setTimeout(() => layer.remove(), 2500);
  }

  function showToast(message, type = 'info') {
    if (!toastContainer) return;
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    toastContainer.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(12px)';
      setTimeout(() => toast.remove(), 200);
    }, 2200);
  }

  function capitalize(s) { return s.charAt(0).toUpperCase() + s.slice(1); }
})();
