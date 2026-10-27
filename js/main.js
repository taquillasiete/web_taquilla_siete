// Cabecera: gana fondo al hacer scroll
const header = document.querySelector(".site-header");

if (header) {
  const alDesplazar = () => {
    header.classList.toggle("con-fondo", window.scrollY > 40);
  };
  alDesplazar();
  window.addEventListener("scroll", alDesplazar, { passive: true });
}

// Menú móvil
const navToggle = document.querySelector(".nav-toggle");
const navLinks = document.querySelector(".nav-links");

if (navToggle && navLinks) {
  const marcarMenu = (abierto) => {
    navLinks.classList.toggle("abierto", abierto);
    navToggle.setAttribute("aria-expanded", String(abierto));
    navToggle.setAttribute("aria-label", abierto ? "Cerrar menú" : "Abrir menú");
  };

  navToggle.addEventListener("click", () => {
    marcarMenu(!navLinks.classList.contains("abierto"));
  });

  navLinks.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", () => marcarMenu(false));
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && navLinks.classList.contains("abierto")) {
      marcarMenu(false);
      navToggle.focus();
    }
  });
}

// Desplegable "Más" (escritorio): se abre con hover o clic; se cierra al hacer clic fuera o con Esc
const navMas = document.querySelector(".nav-mas");

if (navMas) {
  const boton = navMas.querySelector(".nav-mas-boton");
  const cerrar = () => {
    navMas.classList.remove("abierto");
    boton.setAttribute("aria-expanded", "false");
  };

  boton.addEventListener("click", (e) => {
    e.stopPropagation();
    const abierto = navMas.classList.toggle("abierto");
    boton.setAttribute("aria-expanded", String(abierto));
  });
  document.addEventListener("click", (e) => {
    if (!navMas.contains(e.target)) cerrar();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") cerrar();
  });
}

// Reveal on scroll
const revealEls = document.querySelectorAll(".reveal");

if ("IntersectionObserver" in window && revealEls.length) {
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.15 }
  );

  revealEls.forEach((el) => observer.observe(el));
} else {
  revealEls.forEach((el) => el.classList.add("is-visible"));
}
