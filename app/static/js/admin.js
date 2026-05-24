'use strict';

// Toggle companion rows
document.querySelectorAll('.toggle-persons').forEach(btn => {
  btn.addEventListener('click', () => {
    const row = document.getElementById('persons-' + btn.dataset.id);
    const hidden = row.classList.toggle('hidden');
    btn.textContent = hidden ? 'Details' : 'Schließen';
  });
});

// Live search across registrant name and email
const searchInput = document.getElementById('search-input');
if (searchInput) {
  searchInput.addEventListener('input', () => {
    const q = searchInput.value.toLowerCase();
    document.querySelectorAll('.reg-row').forEach(row => {
      const text = row.dataset.search.toLowerCase();
      const visible = text.includes(q);
      row.classList.toggle('hidden', !visible);
      // Always hide companions row when parent is hidden
      const id = row.querySelector('.toggle-persons')?.dataset.id;
      if (id) {
        document.getElementById('persons-' + id)?.classList.add('hidden');
      }
    });
  });
}
