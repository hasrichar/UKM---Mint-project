(function () {
	'use strict'

	var forms = document.querySelectorAll('.needs-validation')

	Array.prototype.slice.call(forms)
		.forEach(function (form) {
			form.addEventListener('submit', function (event) {
				if (!form.checkValidity()) {
					event.preventDefault()
					event.stopPropagation()
				}

				form.classList.add('was-validated')
			}, false)
		})
})()

window.addEventListener('scroll', function(){
	var header = document.querySelector('header');
	header.classList.toggle('sticky', window.scrollY > 0);
})

function openOverlay() {
	document.getElementById("myOverlay").style.display = "block";
}

function closeOverlay() {
	document.getElementById("myOverlay").style.display = "none";
}