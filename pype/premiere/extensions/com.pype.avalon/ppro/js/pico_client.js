// pico connection of python module name
var api = pico.importModule('api');

function querySelector(parent) {
  return function (child) {
    return document.querySelector(parent).querySelector(child)
  };
}

var defs = {}

function jumpTo(name) {
  var e = defs[name];
  document.querySelectorAll('.highlight').forEach(function (el) {
    el.classList.remove('highlight');
  });
  e.classList.add('highlight');
  return false;
}

function unindent(code) {
  var lines = code.split('\n');
  var margin = -1;
  for (var j = 0; j < lines.length; j++) {
    var l = lines[j];
    for (i = 0; i < l.length; i++) {
      if (l[i] != " ") {
        margin = i;
        break;
      }
    }
    if (margin > -1) {
      break;
    }
  }
  lines = lines.slice(j);
  return lines.map(function (s) {
    return s.substr(margin)
  }).join('\n');
}


function ready() {
  // // set the <code> element of each example to the corresponding functions source
  // document.querySelectorAll('li pre code.js').forEach(function(e){
  //   var id = e.parentElement.parentElement.id;
  //   var f = window[id];
  //   var code = f.toString().split('\n').slice(2, -1).join('\n');
  //   e.innerText = unindent(code);
  // })

  document.querySelectorAll('li pre code.html').forEach(function (e) {
    var html = e.parentElement.parentElement.querySelector('div.example').innerHTML;
    e.innerText = unindent(html);
  })

  hljs.initHighlighting();

  // // find all the elements representing the function definitions in the python source
  // document.querySelectorAll('.python .hljs-function .hljs-title').forEach(function(e){
  //   var a = document.createElement('a');
  //   a.name = e.innerText;
  //   e.parentElement.insertBefore(a, e)
  //   return defs[e.innerText] = e.parentElement;
  // });

  // convert all 'api.X' strings to hyperlinks to jump to python source
  document.querySelectorAll('.js').forEach(function (e) {
    var code = e.innerHTML;
    Object.keys(defs).forEach(function (k) {
      code = code.replace('api.' + k + '(', '<a href="#' + k + '" onclick="jumpTo(\'' + k + '\')">api.' + k + '</a>(');
    })
    e.innerHTML = code;
  })
}
