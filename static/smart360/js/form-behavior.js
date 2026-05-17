document.addEventListener("DOMContentLoaded", function () {
  try {
    // Focus first input with a visible error hint
    let err = document.querySelector(".form-error, .errorlist");
    if (err) {
      // prefer input/select/textarea inside same form-field
      let field = err.closest(".form-field");
      if (field) {
        let input = field.querySelector("input, textarea, select");
        if (input) {
          input.focus();
          input.scrollIntoView({ behavior: "smooth", block: "center" });
        }
      } else {
        // fallback: focus first input inside same form
        let form = err.closest("form");
        if (form) {
          let first = form.querySelector("input, textarea, select");
          if (first) {
            first.focus();
            first.scrollIntoView({ behavior: "smooth", block: "center" });
          }
        }
      }
    }
  } catch (e) {
    // noop
    console.warn("form-behavior error", e);
  }
});

