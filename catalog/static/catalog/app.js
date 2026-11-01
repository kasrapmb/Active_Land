const schedule = JSON.parse(document.querySelector('#catalog-schedule').textContent);
document.querySelectorAll('[data-age]').forEach(button => button.addEventListener('click', () => {
  document.querySelectorAll('[data-age]').forEach(item => {
    item.classList.toggle('selected', item === button);
    item.setAttribute('aria-pressed', String(item === button));
  });
  let count = 0;
  document.querySelectorAll('[data-min-age]').forEach(card => {
    card.hidden = button.dataset.age !== 'all' && !(Number(card.dataset.minAge) < (Number(button.dataset.age) + 1) * 12 && Number(card.dataset.maxAge) > Number(button.dataset.age) * 12);
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
    time.textContent = slot.label.replace(/[0-9]/g, digit => '۰۱۲۳۴۵۶۷۸۹'[digit]);
    const link = document.createElement('a');
    link.className = 'outline';
    link.href = slot.url;
    link.textContent = 'انتخاب سانس';
    row.append(label, time, link);
    list.append(row);
  });
  document.querySelector('#sessions').showModal();
}));
document.querySelector('[data-login]')?.addEventListener('click', () => document.querySelector('#login').showModal());
document.querySelectorAll('dialog').forEach(dialog => {
  dialog.querySelector('.close').addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', event => { if (event.target === dialog) {
    const rect = dialog.getBoundingClientRect();
    if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) dialog.close();
  }});
});
