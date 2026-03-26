(function(){
    function getBtn(){
        return document.querySelector('.sidebar-toggle-btn');
    }
    function getZone(){
        return document.querySelector('.sidebar-hover-zone');
    }
    if(!window.__sidebarToggleRuntime){
        var hideTimer = null;
        function clearHide(){
            clearTimeout(hideTimer);
        }
        function showBtn(){
            var btn = getBtn();
            if(!btn) return;
            btn.style.opacity = '1';
            btn.style.pointerEvents = 'auto';
            btn.style.transition = 'opacity 0.2s ease';
        }
        function hideBtn(){
            var btn = getBtn();
            if(!btn) return;
            btn.style.opacity = '0';
            btn.style.pointerEvents = 'none';
            btn.style.transition = 'opacity 0.45s ease';
        }
        function scheduleHide(delay){
            clearHide();
            hideTimer = setTimeout(hideBtn, delay || 2000);
        }
        window.__sidebarToggleRuntime = {
            showBtn: showBtn,
            hideBtn: hideBtn,
            scheduleHide: scheduleHide,
            clearHide: clearHide
        };
        document.addEventListener('mousemove', function(e){
            var zone = getZone();
            if(!zone) return;
            var rect = zone.getBoundingClientRect();
            if(
                e.clientX <= rect.right &&
                e.clientY >= rect.top &&
                e.clientY <= rect.bottom
            ){
                showBtn();
                clearHide();
            }
        });
        document.addEventListener('mouseover', function(e){
            var btn = getBtn();
            if(btn && btn.contains(e.target)){
                clearHide();
            }
        });
        document.addEventListener('mouseout', function(e){
            var btn = getBtn();
            if(btn && btn.contains(e.target)){
                scheduleHide(1800);
            }
        });
        document.addEventListener('touchstart', function(e){
            var zone = getZone();
            if(zone && zone.contains(e.target)){
                showBtn();
                scheduleHide(2200);
                return;
            }
            var btn = getBtn();
            if(btn && btn.contains(e.target)){
                clearHide();
            }
        }, {passive: true});
    }
    setTimeout(function(){
        if(!window.__sidebarToggleRuntime) return;
        window.__sidebarToggleRuntime.showBtn();
        window.__sidebarToggleRuntime.scheduleHide(2200);
    }, 80);
})();
