'use strict';

const step1 = document.getElementById('step-1');
const step2 = document.getElementById('step-2');
const companionsContainer = document.getElementById('companions-container');
const companionCountInput = document.getElementById('companion_count');

function buildCompanionHTML(i) {
  return `
    <div class="companion-group" id="companion-group-${i}">
      <h4>Begleitperson ${i}</h4>
      <div class="form-grid">
        <div class="field" style="grid-column: 1 / -1;">
          <label for="companion_name_${i}">Name *</label>
          <input
            type="text"
            id="companion_name_${i}"
            name="companion_name_${i}"
            placeholder="Vorname Nachname"
            required
            autocomplete="off"
          >
        </div>
        <div class="field">
          <label>Alter *</label>
          <div class="radio-group">
            <label class="radio-label">
              <input type="radio" name="companion_over18_${i}" value="yes" checked>
              <span>Über 18</span>
            </label>
            <label class="radio-label">
              <input type="radio" name="companion_over18_${i}" value="no">
              <span>Unter 18</span>
            </label>
          </div>
        </div>
        <div class="field">
          <label>Essenspräferenz *</label>
          <div class="radio-group">
            <label class="radio-label">
              <input type="radio" name="companion_food_${i}" value="meat" checked>
              <span>🥩 Fleisch</span>
            </label>
            <label class="radio-label">
              <input type="radio" name="companion_food_${i}" value="vegetarian">
              <span>🥗 Vegetarisch</span>
            </label>
          </div>
        </div>
      </div>
    </div>
  `;
}

function renderCompanions(count) {
  companionsContainer.innerHTML = '';
  for (let i = 1; i <= count; i++) {
    companionsContainer.insertAdjacentHTML('beforeend', buildCompanionHTML(i));
  }
}

function validateStep1() {
  const name  = document.getElementById('registrant_name').value.trim();
  const email = document.getElementById('email').value.trim();
  const count = parseInt(companionCountInput.value || '0', 10);
  const errors = [];

  if (!name) errors.push('Dein Name ist erforderlich.');
  if (!email || !email.includes('@') || !email.split('@')[1].includes('.')) {
    errors.push('Bitte gib eine gültige E-Mail-Adresse ein.');
  }
  if (!count || count < 1) errors.push('Mindestens 1 Begleitperson ist erforderlich.');

  return errors;
}

function showStep1Errors(errors) {
  let box = document.getElementById('client-errors');
  if (!box) {
    box = document.createElement('div');
    box.id = 'client-errors';
    box.className = 'error-box';
    step1.insertBefore(box, step1.querySelector('.form-grid'));
  }
  box.innerHTML = '<strong>Bitte korrigiere folgende Fehler:</strong><ul>' +
    errors.map(e => `<li>${e}</li>`).join('') + '</ul>';
}

function clearStep1Errors() {
  document.getElementById('client-errors')?.remove();
}

document.getElementById('btn-to-companions').addEventListener('click', () => {
  const errors = validateStep1();
  if (errors.length) {
    showStep1Errors(errors);
    return;
  }
  clearStep1Errors();

  const count = Math.max(1, parseInt(companionCountInput.value || '1', 10));
  renderCompanions(count);
  step2.classList.remove('hidden');
  step2.scrollIntoView({ behavior: 'smooth', block: 'start' });
});

document.getElementById('btn-back').addEventListener('click', () => {
  step2.classList.add('hidden');
  step1.scrollIntoView({ behavior: 'smooth', block: 'start' });
});

// Re-render companions when count changes while step 2 is visible
companionCountInput.addEventListener('change', () => {
  if (!step2.classList.contains('hidden')) {
    const count = Math.max(1, parseInt(companionCountInput.value || '1', 10));
    renderCompanions(count);
  }
});

// Prevent double-submit
document.getElementById('reg-form').addEventListener('submit', function () {
  this.querySelectorAll('.btn-submit').forEach(btn => {
    btn.disabled = true;
    btn.textContent = 'Wird gesendet…';
  });
});
