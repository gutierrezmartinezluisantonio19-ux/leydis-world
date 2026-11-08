function entrar() {
    const intro = document.getElementById("intro");
    const contenido = document.getElementById("contenido");

    intro.classList.add("oculto");
    contenido.style.display = "block";

    document.body.style.overflow = "auto";
}

document.addEventListener("DOMContentLoaded", function() {
    document.body.style.overflow = "hidden";
});