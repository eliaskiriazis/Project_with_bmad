document.addEventListener('DOMContentLoaded', function () {
  const forms = document.querySelectorAll('form');
  forms.forEach((form) => {
    form.addEventListener('submit', function () {
      form.dataset.submitted = 'true';
    });
  });
  const summary = document.querySelector('#checkout-summary');
  if (summary) {
    const total = summary.querySelector('#checkout-total');
    const shippingFee = Number(summary.dataset.shippingFee);
    const currency = new Intl.NumberFormat(document.documentElement.lang, {
      style: 'currency',
      currency: 'EUR',
    });
    const updateTotal = () => {
      const fulfillment = document.querySelector('[name="fulfillment_method"]')?.value;
      const cents = Number(summary.dataset.itemPrice)
        + (fulfillment === 'pickup' ? 0 : shippingFee);
      total.textContent = currency.format(cents / 100);
    };
    document.querySelectorAll('[name="fulfillment_method"]').forEach((input) => {
      input.addEventListener('change', updateTotal);
    });
    updateTotal();
  });
});
