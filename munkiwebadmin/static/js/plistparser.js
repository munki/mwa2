/**
plistparser.js

Adapted from:

 https://github.com/pugetive/plist_parser
 PlistParser: a JavaScript utility to process Plist XML into JSON
 @author Todd Gehman (toddgehman@gmail.com)
 Copyright (c) 2010 Todd Gehman
 
 some changes 2015 Greg Neagle (gregneagle@mac.com):
    - PlistParser.toPlist now properly generates <array> items
    - PlistParser.toPlist can output "pretty formatted" plist strings
    - collapse "<true></true>" to "<true/>" and "<false></false>" to "<false/>"
    - changes in date handling
    - attempt to handle int/float types
    - work with JavaScript objects instead of JSON strings since JSON is lossy
      with dates (dates are converted to strings, losing their "date"-ness)

 --- 

 Usage:
   var jsobject= PlistParser.parse(xmlString);
   var plistString = PlistParser.toPlist(jsobject);
 ---

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
*/

var PlistParser = {};

PlistParser.parse = function(plist_xml){
    // parses a plist (text format only) into a JavaScript object
    var parser = new DOMParser();
    plist_xml = parser.parseFromString(plist_xml, 'text/xml');
    
    var result = this._xml_to_js(plist_xml.getElementsByTagName('plist').item(0));
  return result;
};

PlistParser._xml_to_js = function(xml_node) {
  var parser = this;
  var parent_node = xml_node;
  var parent_node_name = parent_node.nodeName;

  var child_nodes = [];
  for(var i = 0; i < parent_node.childNodes.length; ++i){
    var child = parent_node.childNodes.item(i);
    if (child.nodeName != '#text'){
      child_nodes.push(child);
    };
  };
  
  switch(parent_node_name){

    case 'plist':
      
      return parser._xml_to_js(child_nodes[0]);

    case 'dict':

      var dictionary = {};
      var key_name;
      var key_value;
      for(var i = 0; i < child_nodes.length; ++i){
        var child = child_nodes[i];
        if (child.nodeName == '#text'){
          // ignore empty text children
        } else if (child.nodeName == 'key'){
          key_name = PlistParser._textValue(child.firstChild);
        } else {
          key_value = parser._xml_to_js(child);
          dictionary[key_name] = key_value;
        }
      }

      return dictionary;

    case 'array':

      var standard_array = [];
      for(var i = 0; i < child_nodes.length; ++i){
        var child = child_nodes[i];
        standard_array.push(parser._xml_to_js(child));
      }
      return standard_array;

    case 'string':

      return PlistParser._textValue(parent_node);

    case 'date':

      var textvalue = PlistParser._textValue(parent_node),
          timestamp = Date.parse(textvalue);
      if (isNaN(timestamp)) {
          if (window.console) { 
              console.error('Invalid date string in plist: ' + textvalue);
          }
          timestamp = 0; 
      }
      return new Date(timestamp);

    case 'integer':
    
      // Second argument (radix parameter) forces string to be interpreted in 
      // base 10.
      return parseInt(PlistParser._textValue(parent_node), 10);

    case 'real':
    
      return parseFloat(PlistParser._textValue(parent_node));

    case 'data':

    // TO-DO: we should define a data object so we can differentiate between
    // string and data objects
      return PlistParser._textValue(parent_node);

    case 'true':

      return true;

    case 'false':

      return false;

  };
};


PlistParser._textValue = function(node) {
  if (node.text){
    return node.text;
  } else {
    return node.textContent;
  };
};


PlistParser.toPlist = function(obj, formatted) {

  var walkObj = function(target, obj, callback){
    for(var i in obj){
      if (obj.hasOwnProperty(i)) {
          callback(target, i, obj[i]);
      }
    }
  }

  var walkArray = function(target, arr, callback){
    for (var i=0; i<arr.length; ++i) {
        callback(target, null, arr[i]);
    }
  }

  var isArray = function(o) { 
      return Object.prototype.toString.call(o) == '[object Array]'; }

  var isInt = function(n) {
     return n % 1 === 0;
  }

  var processObject = function(target, name, value) {
    if (name) {
        var key = document.createElement('key');
        key.innerHTML = name;
        target.appendChild(key);
    }
    if (isArray(value)) {
        var arr = document.createElement('array');
        walkArray(arr, value, processObject);
        target.appendChild(arr);
    } else if (typeof value == 'object') {
        if (value instanceof Date) {
            var date = document.createElement('date');
            date.innerHTML = value.toISOString().slice(0, 19) + 'Z';
            target.appendChild(date);
        } else {
            var dict = document.createElement('dict');
            walkObj(dict, value, processObject);
            target.appendChild(dict);
        }
    } else if (typeof value == 'boolean') {
        var bool = document.createElement(value.toString());
        target.appendChild(bool);
    } else if (typeof value == 'number') {
        if (isInt(value)) {
            var num = document.createElement('integer');
        } else {
            var num = document.createElement('real');
        }
        num.innerHTML = value;
        target.appendChild(num);
    } else {
        var string = document.createElement('string');
        string.textContent = value;
        target.appendChild(string);
    }
  };
  
  var formatXml = function(xml) {
    // credit to https://gist.github.com/kurtsson/3f1c8efc0ccd549c9e31
    var formatted = '';
    var reg = /(>)(<)(\/*)/g;
    xml = xml.toString().replace(reg, '$1\r\n$2$3');
    var pad = 0;
    var nodes = xml.split('\r\n');
    for(var n in nodes) {
      var node = nodes[n];
      var indent = 0;
      if (node.match(/.+<\/\w[^>]*>$/)) {
        indent = 0;
      } else if (node.match(/^<\/\w/)) {
        if (pad !== 0) {
          pad -= 1;
        }
      } else if (node.match(/^<\w[^>]*[^\/]>.*$/)) {
        indent = 1;
      } else {
        indent = 0;
      }

      var padding = '';
      for (var i = 0; i < pad; i++) {
        padding += '  ';
      }

      formatted += padding + node + '\r\n';
      pad += indent;
    }
    return formatted;
  };
 
  var xml = '<?xml version="1.0" encoding="UTF-8"?>';
  xml += '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">';

  var container = document.createElement('xml');
  var plist = document.createElement('plist');
  plist.setAttribute('version','1.0');
  container.appendChild(plist);

  if (isArray(obj)) {
      var root = document.createElement('array');
      plist.appendChild(root);
      walkArray(root, obj, processObject);
  } else {
      var root = document.createElement('dict');
      plist.appendChild(root);
      walkObj(root, obj, processObject);
  }
  
  var plist = container.innerHTML;
  // collapse the boolean values to something more commonly seen
  // we could collapse empty arrays and dicts, too, but I don't want to
  // since the 'expanded' version is more convenient to work with in
  // a text editor
  plist = plist.split('<true></true>').join('<true/>');
  plist = plist.split('<false></false>').join('<false/>');
  
  if (formatted) {
      // temporarily collapse empty strings so the formatting code doesn't
      // split the tags across lines
      plist = plist.split('<string></string>').join('<string/>');
      formatted_xml = formatXml(xml + plist);
      //re-expand the empty string tags
      formatted_xml = formatted_xml.split('<string/>').join('<string></string>');
      return formatted_xml;
  }
  return xml + plist;
};
