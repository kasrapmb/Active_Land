const schedule = {
  candy: {name: 'نقل و نبات', slots: ['شنبه · ۱۹ تا ۲۰', 'چهارشنبه · ۱۸ تا ۱۹']},
  honey: {name: 'قند و عسل', slots: ['دوشنبه · ۱۶ تا ۱۷', 'سه‌شنبه · ۱۶ تا ۱۷']},
  heart: {name: 'دردونه', slots: ['شنبه · ۱۸ تا ۱۹']},
  sprout: {name: 'جوونه', slots: ['دوشنبه · ۱۷ تا ۱۸:۳۰']}
};
document.querySelectorAll('[data-age]').forEach(button => button.addEventListener('click', () => {
  document.querySelectorAll('[data-age]').forEach(item => {
    item.classList.toggle('selected', item === button);
    item.setAttribute('aria-pressed', String(item === button));
  });
  let count = 0;
  document.querySelectorAll('[data-group]').forEach(card => {
    card.hidden = button.dataset.age !== 'all' && card.dataset.group !== button.dataset.age;
    if (!card.hidden) count++;
  });
  document.querySelector('.filter-status').textContent = `${count.toLocaleString('fa-IR')} کلاس نمایش داده می‌شود`;
}));
document.querySelectorAll('[data-class]').forEach(button => button.addEventListener('click', () => {
  const item = schedule[button.dataset.class];
  document.querySelector('#dialog-title').textContent = item.name;
  const list = document.querySelector('#session-list');
  list.replaceChildren();
  item.slots.forEach((slot, index) => {
    const row = document.createElement('div');
    row.className = 'slot';
    const label = document.createElement('b');
    label.textContent = `سانس ${(index + 1).toLocaleString('fa-IR')}`;
    const time = document.createElement('span');
    time.textContent = slot;
    row.append(label, time);
    list.append(row);
  });
  document.querySelector('#sessions').showModal();
}));
document.querySelector('[data-login]').addEventListener('click', () => document.querySelector('#login').showModal());
document.querySelectorAll('dialog').forEach(dialog => {
  dialog.querySelector('.close').addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', event => { if (event.target === dialog) {
    const rect = dialog.getBoundingClientRect();
    if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) dialog.close();
  }});
});
