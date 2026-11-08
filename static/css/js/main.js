function entrar() {
    const intro = document.getElementById("intro");

    intro.classList.add("oculto");

    document.body.style.overflow = "auto";
}

document.addEventListener("DOMContentLoaded", function() {
    document.body.style.overflow = "hidden";
});