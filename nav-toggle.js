(function () {
    function initToggle(btn) {
        const targetId = btn.getAttribute('aria-controls');
        const nav = targetId ? document.getElementById(targetId) : btn.nextElementSibling;
        if (!nav) return;
        // initialize button class from aria state
        if (btn.getAttribute('aria-expanded') === 'true') btn.classList.add('is-open');

        // store original parent so we can re-attach when closed
        const originalParent = nav.parentNode;
        const originalNext = nav.nextSibling;

        btn.addEventListener('click', function () {
            const open = this.getAttribute('aria-expanded') === 'true';
            const willOpen = !open;
            this.setAttribute('aria-expanded', String(willOpen));
            nav.setAttribute('data-open', String(willOpen));
            this.classList.toggle('is-open', willOpen);

            if (willOpen) {
                // move nav to body so it escapes any local stacking/overflow contexts
                if (nav.parentNode !== document.body) {
                    document.body.appendChild(nav);
                }
                // position it under the header
                const header = document.querySelector('.site-header');
                const headerRect = header ? header.getBoundingClientRect() : { bottom: 56 };
                nav.style.position = 'fixed';
                nav.style.left = '0px';
                nav.style.right = '0px';
                nav.style.top = Math.round(headerRect.bottom) + 'px';
            } else {
                // restore nav to original location and clear inline positioning
                if (originalParent) {
                    if (originalNext && originalNext.parentNode === originalParent) {
                        originalParent.insertBefore(nav, originalNext);
                    } else {
                        originalParent.appendChild(nav);
                    }
                }
                nav.style.position = '';
                nav.style.left = '';
                nav.style.right = '';
                nav.style.top = '';
            }
        });
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') {
                btn.setAttribute('aria-expanded', 'false');
                nav.setAttribute('data-open', 'false');
                btn.classList.remove('is-open');
                // restore nav position
                if (originalParent) {
                    if (originalNext && originalNext.parentNode === originalParent) {
                        originalParent.insertBefore(nav, originalNext);
                    } else {
                        originalParent.appendChild(nav);
                    }
                }
                nav.style.position = '';
                nav.style.left = '';
                nav.style.right = '';
                nav.style.top = '';
            }
        });
        window.addEventListener('resize', function () {
            if (window.innerWidth > 820) {
                btn.setAttribute('aria-expanded', 'false');
                nav.setAttribute('data-open', 'false');
                btn.classList.remove('is-open');
                // restore nav position on resize
                if (originalParent) {
                    if (originalNext && originalNext.parentNode === originalParent) {
                        originalParent.insertBefore(nav, originalNext);
                    } else {
                        originalParent.appendChild(nav);
                    }
                }
                nav.style.position = '';
                nav.style.left = '';
                nav.style.right = '';
                nav.style.top = '';
            }
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        document.querySelectorAll('.nav-toggle').forEach(initToggle);
    });
})();
