var api = pico.importModule('api');

var output = document.getElementById('output');

function querySelector(parent){
  return function(child){
    return document.querySelector(parent).querySelector(child)
  };
}

var defs = {}
function jumpTo(name){
  var e = defs[name];
  document.querySelectorAll('.highlight').forEach(function(el){
    el.classList.remove('highlight');
  });
  e.classList.add('highlight');
  return false;
}

function displayResult(r){
  output.classList.remove("error");
  output.innerText = JSON.stringify(r);
}

function displayError(e){
  output.classList.add("error");
  output.innerText = e.message;
}

function unindent(code){
  var lines = code.split('\n');
  var margin = -1;
  for(var j=0; j < lines.length; j++){
    var l = lines[j];
    for(i=0; i < l.length; i++){
      if(l[i] != " "){
        margin = i;
        break;
      }
    }
    if(margin > -1){
      break;
    }
  }
  lines = lines.slice(j);
  return lines.map(function(s){ return s.substr(margin)}).join('\n');
}




//
// function example1(){
//   var $ = querySelector("#example1");
//   var name = $("input[name=name]").value;
//   api.hello(name).then(displayResult);
// }
//
//
// function example2(){
//   var $ = querySelector("#example2");
//   var x = $("input[name=x]").valueAsNumber;
//   var y = $("#example2 input[name=y]").valueAsNumber;
//   api.multiply(x, y).then(displayResult);
// }
//
// function example3(){
//   var $ = querySelector("#example3");
//   var file = $("input[name=upload]").files[0];
//   api.upload(file, file.name).then(displayResult).catch(displayError);
// }
//
// function example4(){
//   var $ = querySelector("#example4");
//   api.my_ip().then(displayResult)
// }
//
// function example5(){
//   var $ = querySelector("#example5");
//   var username = $("input[name=username]").value;
//   var password = $("input[name=password]").value;
//   pico.setAuthentication(api, username, password);
//   api.current_user().then(displayResult).catch(displayError);
//   pico.clearAuthentication(api);
// }
//
// function example6(){
//   var $ = querySelector("#example6");
//   api.start_session().then(function(){
//     api.session_id().then(displayResult).then(function(){
//       api.end_session();
//     })
//   })
// }
//
// function example7(){
//   var $ = querySelector("#example7");
//   var session_id = "4242";
//   pico.setRequestHook(api, 'session', function(req) {
//     req.headers.set('X-SESSION-ID', session_id)
//   })
//   api.session_id2().then(displayResult)
//   pico.clearRequestHook(api, 'session');
// }
//
// function example8(){
//   var $ = querySelector("#example8");
//   api.countdown(10).each(displayResult).then(function(){
//     displayResult("Boom!");
//   });
// }
//
// function example9(){
//   var $ = querySelector("#example9");
//   var user = {
//     name: "Bob",
//     age: 30,
//     occupation: "Software Engineer",
//   }
//   api.user_description(user).then(displayResult);
// }
//
// function example10(){
//   var $ = querySelector("#example10");
//   api.fail().then(displayResult).catch(displayError);
// }
//
// function example11(){
//   var $ = querySelector("#example11");
//   api.make_coffee().then(displayResult).catch(displayError);
// }
//
//
// function example12(){
//   var $ = querySelector("#example12");
//   var form = $("form");
//   api.multiply.submitFormData(new FormData(form)).then(displayResult).catch(displayError);
// }
//
// function example13(){
//   var $ = querySelector("#example13");
//   var data = {
//     x: 6,
//     y: 7,
//   }
//   api.multiply.submitJSON(data).then(displayResult).catch(displayError);
// }


// api.show_source().then(function(s){
//   document.querySelector('#source code').innerText = s;
// }).then(ready);


function ready(){
  // // set the <code> element of each example to the corresponding functions source
  // document.querySelectorAll('li pre code.js').forEach(function(e){
  //   var id = e.parentElement.parentElement.id;
  //   var f = window[id];
  //   var code = f.toString().split('\n').slice(2, -1).join('\n');
  //   e.innerText = unindent(code);
  // })

  document.querySelectorAll('li pre code.html').forEach(function(e){
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
  document.querySelectorAll('.js').forEach(function(e){
    var code = e.innerHTML;
    Object.keys(defs).forEach(function(k){
       code = code.replace('api.' + k + '(', '<a href="#' + k + '" onclick="jumpTo(\'' + k + '\')">api.' + k + '</a>(');
    })
    e.innerHTML = code;
  })
}
