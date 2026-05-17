;(function($){

$(document).ready(function(){

//========== HEADER ACTIVE STRATS ============= //
 var windowOn = $(window);
 windowOn.on('scroll', function () {
   var scroll = windowOn.scrollTop();
   if (scroll < 100) {
     $("#vl-header-sticky").removeClass("header-sticky");
   } else {
     $("#vl-header-sticky").addClass("header-sticky");
   }
 });
 
//========== HEADER ACTIVE ENDS ============= //

//========== MOBILE MENU STARTS ============= //
  var vlMenuWrap = $('.vl-mobile-menu-active > ul').clone();
  var vlSideMenu = $('.vl-offcanvas-menu nav');
  vlSideMenu.append(vlMenuWrap);
  if ($(vlSideMenu).find('.sub-menu, .vl-mega-menu').length != 0) {
    $(vlSideMenu).find('.sub-menu, .vl-mega-menu').parent().append('<button class="vl-menu-close"><i class="fas fa-chevron-right"></i></button>');
  }

  var sideMenuList = $('.vl-offcanvas-menu nav > ul > li button.vl-menu-close, .vl-offcanvas-menu nav > ul li.has-dropdown > a');
  $(sideMenuList).on('click', function (e) {
    console.log(e);
    e.preventDefault();
    if (!($(this).parent().hasClass('active'))) {
      $(this).parent().addClass('active');
      $(this).siblings('.sub-menu, .vl-mega-menu').slideDown();
    } else {
      $(this).siblings('.sub-menu, .vl-mega-menu').slideUp();
      $(this).parent().removeClass('active');
    }
  });


$(".vl-offcanvas-toggle").on('click',function(){
  $(".vl-offcanvas").addClass("vl-offcanvas-open");
  $(".vl-offcanvas-overlay").addClass("vl-offcanvas-overlay-open");
});

$(".vl-offcanvas-close-toggle,.vl-offcanvas-overlay").on('click', function(){
  $(".vl-offcanvas").removeClass("vl-offcanvas-open");
  $(".vl-offcanvas-overlay").removeClass("vl-offcanvas-overlay-open");
});

//========== MOBILE MENU ENDS ============= //

  //========== PAGE PROGRESS STARTS ============= // 
  var progressPath = document.querySelector(".progress-wrap path");
  var pathLength = progressPath.getTotalLength();
  progressPath.style.transition = progressPath.style.WebkitTransition =
    "none";
  progressPath.style.strokeDasharray = pathLength + " " + pathLength;
  progressPath.style.strokeDashoffset = pathLength;
  progressPath.getBoundingClientRect();
  progressPath.style.transition = progressPath.style.WebkitTransition =
    "stroke-dashoffset 10ms linear";
  var updateProgress = function () {
    var scroll = $(window).scrollTop();
    var height = $(document).height() - $(window).height();
    var progress = pathLength - (scroll * pathLength) / height;
    progressPath.style.strokeDashoffset = progress;
  };
  updateProgress();
  $(window).scroll(updateProgress);
  var offset = 50;
  var duration = 550;
  jQuery(window).on("scroll", function () {
    if (jQuery(this).scrollTop() > offset) {
      jQuery(".progress-wrap").addClass("active-progress");
    } else {
      jQuery(".progress-wrap").removeClass("active-progress");
    }
  });
  jQuery(".progress-wrap").on("click", function (event) {
    event.preventDefault();
    jQuery("html, body").animate({ scrollTop: 0 }, duration);
    return false;
  });
//========== PAGE PROGRESS STARTS ============= // 

//========== TOGGOL PRICING AREA ============= //
$("#ce-toggle").click(function (event) {
  $(".plan-toggle-wrap").toggleClass("active");
});

$("#ce-toggle").change(function () {
  if ($(this).is(":checked")) {
    $(".tab-content #yearly").hide();
    $(".tab-content #monthly").show();
  } else {
    $(".tab-content #yearly").show();
    $(".tab-content #monthly").hide();
  }
});

$("#ce-toggle1").click(function (event) {
  $(".plan-toggle-wrap1").toggleClass("active");
});

$("#ce-toggle1").change(function () {
  if ($(this).is(":checked")) {
    $(".tab-content #yearly1").hide();
    $(".tab-content #monthly1").show();
  } else {
    $(".tab-content #yearly1").show();
    $(".tab-content #monthly1").hide();
  }
});
//========== TOGGOL PRICING AREA ============= //

//========== PROGRESS ACTIVE ENDS ============= //

//========== PRICING AREA ============= //

//========== VIDEO POPUP STARTS ============= //
   if ($(".popup-youtube").length > 0) {
    $(".popup-youtube").magnificPopup({
    type: "iframe",
    });
    }
//========== VIDEO POPUP ENDS ============= //
AOS.init;
AOS.init({disable: 'mobile'});

//========== NICE SELECT ============= //
$('select').niceSelect();

//========== CASE IMAGE ============= //

});
//========== COUNTER UP============= //
const ucounter = $('.counter');
if (ucounter.length > 0) {
 ucounter.countUp();  
};

//========== TESTIMONIAL AREA ============= //
// testimonial //
$('.case-slider-widget').owlCarousel({
  loop:true,
  margin:30,
  nav:true,
  dots:false,
  items:10,
  navText:["<i class='fa-solid fa-angle-left'></i>","<i class='fa-solid fa-angle-right'></i>"],
  autoplay:true,
  smartSpeed:1500,
  autoplayTimeout:3000,
  responsiveClass:true,
  responsive:{
  0:{
    items:1,                
  },
  600:{
    items:1,
  },
  1000:{
    items:2,
  }
  }
});

// testimonial//
 $('.slider-galeria').slick({
  slidesToShow: 1,
  slidesToScroll: 1,
  arrows: true,
  infinite: false,
  infinite:true,
  asNavFor: '.slider-galeria-thumbs',
  prevArrow: $('.testimonial-next-arrow'),
  nextArrow: $('.testimonial-prev-arrow'),
});
$('.slider-galeria-thumbs').slick({
  slidesToShow: 4,
  slidesToScroll: 1,
  items:15,
  arrows: true,
  asNavFor: '.slider-galeria',
  vertical: true,
  infinite:true,
  verticalSwiping: true,
  focusOnSelect: true,
  infinite: false,
  prevArrow: $('.testimonial-next-arrow'),
  nextArrow: $('.testimonial-prev-arrow'),
});

// testimonial //
$('.testimonial4-slider').owlCarousel({
  loop:true,
  margin:30,
  nav:true,
  dots:false,
  items:10,
  navText:["<i class='fa-solid fa-angle-left'></i>","<i class='fa-solid fa-angle-right'></i>"],
  autoplay:true,
  smartSpeed:1500,
  autoplayTimeout:3000,
  responsiveClass:true,
  responsive:{
  0:{
    items:1,                
  },
  600:{
    items:2,
  },
  1000:{
    items:3,
  }
  }
});

// testimonial //
$('.case4-slider').owlCarousel({
  loop:true,
  margin:30,
  nav:true,
  dots:false,
  items:10,
  navText:["<i class='fa-solid fa-angle-left'></i>","<i class='fa-solid fa-angle-right'></i>"],
  autoplay:true,
  smartSpeed:1500,
  autoplayTimeout:3000,
  responsiveClass:true,
  responsive:{
  0:{
    items:1,                
  },
  600:{
    items:2,
  },
  1000:{
    items:3,
  }
  }
});

// testimonial //
$('.service5-slider-box').owlCarousel({
  loop:true,
  margin:30,
  nav:true,
  dots:false,
  items:10,
  navText:["<i class='fa-solid fa-angle-left'></i>","<i class='fa-solid fa-angle-right'></i>"],
  autoplay:true,
  smartSpeed:1500,
  autoplayTimeout:3000,
  responsiveClass:true,
  responsive:{
  0:{
    items:1,                
  },
  600:{
    items:2,
  },
  1000:{
    items:3,
  }
  }
});
//========== PRELOADER ============= //
$(window).on("load", function (event) {
  setTimeout(function () {
    $(".preloader").fadeToggle();
  }, 200);

});
//========== PROGRESS BAR AREA ============= //

//========== PARALLAX AREA ============= //
})(jQuery);


//========== GSAP AREA ============= //

if ($('.text-anime-style-1').length) {
  let staggerAmount 	= 0.05,
  translateXValue = 0,
  delayValue 		= 0.5,
   animatedTextElements = document.querySelectorAll('.text-anime-style-1');

  animatedTextElements.forEach((element) => {
  let animationSplitText = new SplitText(element, { type: "chars, words" });
    gsap.from(animationSplitText.words, {
    duration: 1,
    delay: delayValue,
    x: 20,
    autoAlpha: 0,
    stagger: staggerAmount,
    scrollTrigger: { trigger: element, start: "top 85%" },
    });
  });
  }

  if ($('.text-anime-style-2').length) {
  let	 staggerAmount 		= 0.05,
   translateXValue	= 20,
   delayValue 		= 0.5,
   easeType 			= "power2.out",
   animatedTextElements = document.querySelectorAll('.text-anime-style-2');

  animatedTextElements.forEach((element) => {
  let animationSplitText = new SplitText(element, { type: "chars, words" });
    gsap.from(animationSplitText.chars, {
      duration: 1,
      delay: delayValue,
      x: translateXValue,
      autoAlpha: 0,
      stagger: staggerAmount,
      ease: easeType,
      scrollTrigger: { trigger: element, start: "top 85%"},
    });
  });
  }

  if ($('.text-anime-style-3').length) {
  let	animatedTextElements = document.querySelectorAll('.text-anime-style-3');

  animatedTextElements.forEach((element) => {
  //Reset if needed
  if (element.animation) {
    element.animation.progress(1).kill();
    element.split.revert();
  }

  element.split = new SplitText(element, {
    type: "lines,words,chars",
    linesClass: "split-line",
  });
  gsap.set(element, { perspective: 400 });

  gsap.set(element.split.chars, {
    opacity: 0,
    x: "50",
  });

  element.animation = gsap.to(element.split.chars, {
    scrollTrigger: { trigger: element,	start: "top 90%" },
    x: "0",
    y: "0",
    rotateX: "0",
    opacity: 1,
    duration: 1,
    ease: Back.easeOut,
    stagger: 0.02,
  });
  });
  }

  if($('.reveal').length){gsap.registerPlugin(ScrollTrigger);let revealContainers=document.querySelectorAll(".reveal");revealContainers.forEach((container)=>{let image=container.querySelector("img");let tl=gsap.timeline({scrollTrigger:{trigger:container,toggleActions:"play none none none"}});tl.set(container,{autoAlpha:1});tl.from(container,1.5,{xPercent:-100,ease:Power2.out});tl.from(image,1.5,{xPercent:100,scale:1.3,delay:-1.5,ease:Power2.out});});}

  function animateElements() {
    $('.progressbar').each(function () {
      var elementPos = $(this).offset().top;
      var topOfWindow = $(window).scrollTop();
      var percent = $(this).find('.circle').attr('data-percent');
      var percentage = parseInt(percent, 10) / parseInt(100, 10);
      var animate = $(this).data('animate');
      if (elementPos < topOfWindow + $(window).height() - 10 && !animate) {
        $(this).data('animate', true);
        $(this).find('.circle').circleProgress({
          startAngle: -Math.PI / 2,
          value: percent / 100,
          size: 80,
          thickness: 5,
          emptyFill: "#E6E6EB",
          fill: {
            color: '#2E0797'
          }
        }).on('circle-animation-progress', function (event, progress, stepValue) {
          $(this).find('div').text((stepValue*100).toFixed() + "%");
        }).stop();
      }
    });
  }
  
  // Show animated elements
  animateElements();
  $(window).scroll(animateElements);