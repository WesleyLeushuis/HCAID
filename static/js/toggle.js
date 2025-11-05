document.addEventListener('DOMContentLoaded', () => {
  const sw = document.getElementById('modeSwitch');
  if (!sw) return;

  async function saveFormIfAny() {
    const form = document.querySelector('form');
    if (!form) return;

    const data = {};
    // Pak zowel inputs als selects en textareas
    const fields = form.querySelectorAll('input, select, textarea');
    fields.forEach(el => {
      if (!el.name) return;
      if (el.type === 'checkbox') {
        data[el.name] = el.checked ? 'on' : '';
      } else {
        data[el.name] = el.value ?? '';
      }
    });

    try {
      await fetch('/save-form', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
      });
    } catch (e) {
      // stil falen – toggle moet niet blokkeren
      console.warn('save-form failed:', e);
    }
  }

  sw.addEventListener('change', async () => {
    const url = sw.checked ? sw.dataset.badUrl : sw.dataset.goodUrl;
    await saveFormIfAny(); // eerst opslaan
    window.location.href = url;
  });
});
