/*
 *  Angular RangeSlider Directive
 * 
 *  Version: 0.0.13
 *
 *  Author: Daniel Crisp, danielcrisp.com
 *
 *  The rangeSlider has been styled to match the default styling
 *  of form elements styled using Twitter's Bootstrap
 *
 *  Originally forked from https://github.com/leongersen/noUiSlider
 *

    This code is released under the MIT Licence - http://opensource.org/licenses/MIT

    Copyright (c) 2013 Daniel Crisp

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

(function() {
    'use strict';

    // check if we need to support legacy angular
    var legacySupport = (angular.version.major === 1 && angular.version.minor === 0);

    /**
     * RangeSlider, allows user to define a range of values using a slider
     * Touch friendly.
     * @directive
     */
    angular.module('ui-rangeSlider', [])
        .directive('rangeSlider', ['$document', '$filter', '$log', function($document, $filter, $log) {

            // test for mouse, pointer or touch
            var eventNamespace = '.rangeSlider',

                defaults = {
                    disabled: false,
                    orientation: 'horizontal',
                    step: 0,
                    decimalPlaces: 0,
                    showValues: true,
                    preventEqualMinMax: false,
                    attachHandleValues: false
                },

                // Determine the events to bind. IE11 implements pointerEvents without
                // a prefix, which breaks compatibility with the IE10 implementation.
                /** @const */
                actions = window.navigator.pointerEnabled ? {
                    start: 'pointerdown',
                    move: 'pointermove',
                    end: 'pointerup',
                    over: 'pointerdown',
                    out: 'mouseout'
                } : window.navigator.msPointerEnabled ? {
                    start: 'MSPointerDown',
                    move: 'MSPointerMove',
                    end: 'MSPointerUp',
                    over: 'MSPointerDown',
                    out: 'mouseout'
                } : {
                    start: 'mousedown touchstart',
                    move: 'mousemove touchmove',
                    end: 'mouseup touchend',
                    over: 'mouseover touchstart',
                    out: 'mouseout'
                },

                onEvent = actions.start + eventNamespace,
                moveEvent = actions.move + eventNamespace,
                offEvent = actions.end + eventNamespace,
                overEvent = actions.over + eventNamespace,
                outEvent = actions.out + eventNamespace,

                // get standarised clientX and clientY
                client = function(f) {
                    try {
                        return [(f.clientX || f.originalEvent.clientX || f.originalEvent.touches[0].clientX), (f.clientY || f.originalEvent.clientY || f.originalEvent.touches[0].clientY)];
                    } catch (e) {
                        return ['x', 'y'];
                    }
                },

                restrict = function(value) {

                    // normalize so it can't move out of bounds
                    return (value < 0 ? 0 : (value > 100 ? 100 : value));

                },

                isNumber = function(n) {
                    // console.log(n);
                    return !isNaN(parseFloat(n)) && isFinite(n);
                },

                scopeOptions = {
                    disabled: '=?',
                    min: '=',
                    max: '=',
                    modelMin: '=?',
                    modelMax: '=?',
                    onHandleDown: '&', // calls optional function when handle is grabbed
                    onHandleUp: '&', // calls optional function when handle is released
                    orientation: '@', // options: horizontal | vertical | vertical left | vertical right
                    step: '@',
                    decimalPlaces: '@',
                    filter: '@',
                    filterOptions: '@',
                    showValues: '@',
                    pinHandle: '@',
                    preventEqualMinMax: '@',
                    attachHandleValues: '@',
                    getterSetter: '@' // Allow the use of getterSetters for model values
                };

            if (legacySupport) {
                // make optional properties required
                scopeOptions.disabled = '=';
                scopeOptions.modelMin = '=';
                scopeOptions.modelMax = '=';
            }

            // if (EVENT < 4) {
            //     // some sort of touch has been detected
            //     angular.element('html').addClass('ngrs-touch');
            // } else {
            //     angular.element('html').addClass('ngrs-no-touch');
            // }


            return {
                restrict: 'A',
                replace: true,
                template: ['<div class="ngrs-range-slider">',
                    '<div class="ngrs-runner">',
                    '<div class="ngrs-handle ngrs-handle-min"><i></i></div>',
                    '<div class="ngrs-handle ngrs-handle-max"><i></i></div>',
                    '<div class="ngrs-join"></div>',
                    '</div>',
                    '<div class="ngrs-value-runner">',
                    '<div class="ngrs-value ngrs-value-min" ng-show="showValues"><div>{{filteredModelMin}}</div></div>',
                    '<div class="ngrs-value ngrs-value-max" ng-show="showValues"><div>{{filteredModelMax}}</div></div>',
                    '</div>',
                    '</div>'
                ].join(''),
                scope: scopeOptions,
                link: function(scope, element, attrs, controller) {

                    /**
                     *  FIND ELEMENTS
                     */

                    var $slider = angular.element(element),
                        handles = [element.find('.ngrs-handle-min'), element.find('.ngrs-handle-max')],
                        values = [element.find('.ngrs-value-min'), element.find('.ngrs-value-max')],
                        join = element.find('.ngrs-join'),
                        pos = 'left',
                        posOpp = 'right',
                        orientation = 0,
                        allowedRange = [0, 0],
                        range = 0,
                        down = false;

                    // filtered
                    scope.filteredModelMin = modelMin();
                    scope.filteredModelMax = modelMax();

                    /**
                     *  FALL BACK TO DEFAULTS FOR SOME ATTRIBUTES
                     */

                    attrs.$observe('disabled', function(val) {
                        if (!angular.isDefined(val)) {
                            scope.disabled = defaults.disabled;
                        }

                        scope.$watch('disabled', setDisabledStatus);
                    });

                    attrs.$observe('orientation', function(val) {
                        if (!angular.isDefined(val)) {
                            scope.orientation = defaults.orientation;
                        }

                        var classNames = scope.orientation.split(' '),
                            useClass;

                        for (var i = 0, l = classNames.length; i < l; i++) {
                            classNames[i] = 'ngrs-' + classNames[i];
                        }

                        useClass = classNames.join(' ');

                        // add class to element
                        $slider.addClass(useClass);

                        // update pos
                        if (scope.orientation === 'vertical' || scope.orientation === 'vertical left' || scope.orientation === 'vertical right') {
                            pos = 'top';
                            posOpp = 'bottom';
                            orientation = 1;
                        }
                    });

                    attrs.$observe('step', function(val) {
                        if (!angular.isDefined(val)) {
                            scope.step = defaults.step;
                        }
                    });

                    attrs.$observe('decimalPlaces', function(val) {
                        if (!angular.isDefined(val)) {
                            scope.decimalPlaces = defaults.decimalPlaces;
                        }
                    });

                    attrs.$observe('showValues', function(val) {
                        if (!angular.isDefined(val)) {
                            scope.showValues = defaults.showValues;
                        } else {
                            if (val === 'false') {
                                scope.showValues = false;
                            } else {
                                scope.showValues = true;
                            }
                        }
                    });

                    attrs.$observe('pinHandle', function(val) {
                        if (!angular.isDefined(val)) {
                            scope.pinHandle = null;
                        } else {
                            if (val === 'min' || val === 'max') {
                                scope.pinHandle = val;
                            } else {
                                scope.pinHandle = null;
                            }
                        }

                        scope.$watch('pinHandle', setPinHandle);
                    });

                    attrs.$observe('preventEqualMinMax', function(val) {
                        if (!angular.isDefined(val)) {
                            scope.preventEqualMinMax = defaults.preventEqualMinMax;
                        } else {
                            if (val === 'false') {
                                scope.preventEqualMinMax = false;
                            } else {
                                scope.preventEqualMinMax = true;
                            }
                        }
                    });

                    attrs.$observe('attachHandleValues', function(val) {
                        if (!angular.isDefined(val)) {
                            scope.attachHandleValues = defaults.attachHandleValues;
                        } else {
                            if (val === 'true' || val === '') {
                                // flag as true
                                scope.attachHandleValues = true;
                                // add class to runner
                                element.find('.ngrs-value-runner').addClass('ngrs-attached-handles');
                            } else {
                                scope.attachHandleValues = false;
                            }
                        }
                    });

                    // GetterSetters for model values

                    function modelMin(newValue) {
                        if(scope.getterSetter) {
                            return arguments.length ? scope.modelMin(newValue) : scope.modelMin();
                        } else {
                            return arguments.length ? (scope.modelMin = newValue) : scope.modelMin;
                        }
                    }

                    function modelMax(newValue) {
                        if(scope.getterSetter) {
                            return arguments.length ? scope.modelMax(newValue) : scope.modelMax();
                        } else {
                            return arguments.length ? (scope.modelMax = newValue) : scope.modelMax;
                        }
                    }

                    // listen for changes to values
                    scope.$watch('min', setMinMax);
                    scope.$watch('max', setMinMax);

                    scope.$watch(function () {
                        return modelMin();
                    }, setModelMinMax);
                    scope.$watch(function () {
                        return modelMax();
                    }, setModelMinMax);

                    /**
                     * HANDLE CHANGES
                     */

                    function setPinHandle(status) {
                        if (status === "min") {
                            angular.element(handles[0]).css('display', 'none');
                            angular.element(handles[1]).css('display', 'block');
                        } else if (status === "max") {
                            angular.element(handles[0]).css('display', 'block');
                            angular.element(handles[1]).css('display', 'none');
                        } else {
                            angular.element(handles[0]).css('display', 'block');
                            angular.element(handles[1]).css('display', 'block');
                        }
                    }

                    function setDisabledStatus(status) {
                        if (status) {
                            $slider.addClass('ngrs-disabled');
                        } else {
                            $slider.removeClass('ngrs-disabled');
                        }
                    }

                    function setMinMax() {

                        if (scope.min > scope.max) {
                            throwError('min must be less than or equal to max');
                        }

                        // only do stuff when both values are ready
                        if (angular.isDefined(scope.min) && angular.isDefined(scope.max)) {

                            // make sure they are numbers
                            if (!isNumber(scope.min)) {
                                throwError('min must be a number');
                            }

                            if (!isNumber(scope.max)) {
                                throwError('max must be a number');
                            }

                            range = scope.max - scope.min;
                            allowedRange = [scope.min, scope.max];

                            // update models too
                            setModelMinMax();

                        }
                    }

                    function setModelMinMax() {

                        if (modelMin() > modelMax()) {
                            throwWarning('modelMin must be less than or equal to modelMax');
                            // reset values to correct
                            modelMin(modelMax());
                        }

                        // only do stuff when both values are ready
                        if (
                            (angular.isDefined(modelMin()) || scope.pinHandle === 'min') &&
                            (angular.isDefined(modelMax()) || scope.pinHandle === 'max')
                        ) {

                            // make sure they are numbers
                            if (!isNumber(modelMin())) {
                                if (scope.pinHandle !== 'min') {
                                    throwWarning('modelMin must be a number');
                                }
                                modelMin(scope.min);
                            }

                            if (!isNumber(modelMax())) {
                                if (scope.pinHandle !== 'max') {
                                    throwWarning('modelMax must be a number');
                                }
                                modelMax(scope.max);
                            }

                            var handle1pos = restrict(((modelMin() - scope.min) / range) * 100),
                                handle2pos = restrict(((modelMax() - scope.min) / range) * 100),
                                value1pos,
                                value2pos;

                            if (scope.attachHandleValues) {
                                value1pos = handle1pos;
                                value2pos = handle2pos;
                            }

                            // make sure the model values are within the allowed range
                            modelMin(Math.max(scope.min, modelMin()));
                            modelMax(Math.min(scope.max, modelMax()));

                            if (scope.filter && scope.filterOptions) {
                                scope.filteredModelMin = $filter(scope.filter)(modelMin(), scope.filterOptions);
                                scope.filteredModelMax = $filter(scope.filter)(modelMax(), scope.filterOptions);
                            } else if (scope.filter) {

                                var filterTokens = scope.filter.split(':'),
                                    filterName = scope.filter.split(':')[0],
                                    filterOptions = filterTokens.slice().slice(1),
                                    modelMinOptions,
                                    modelMaxOptions;

                                // properly parse string and number args
                                filterOptions = filterOptions.map(function (arg) {
                                    if (isNumber(arg)) {
                                        return +arg;
                                    } else if ((arg[0] == "\"" && arg[arg.length-1] == "\"") || (arg[0] == "\'" && arg[arg.length-1] == "\'")) {
                                        return arg.slice(1, -1);
                                    }
                                });

                                modelMinOptions = filterOptions.slice();
                                modelMaxOptions = filterOptions.slice();
                                modelMinOptions.unshift(modelMin());
                                modelMaxOptions.unshift(modelMax());

                                scope.filteredModelMin = $filter(filterName).apply(null, modelMinOptions);
                                scope.filteredModelMax = $filter(filterName).apply(null, modelMaxOptions);
                            } else {
                                scope.filteredModelMin = modelMin();
                                scope.filteredModelMax = modelMax();
                            }

                            // check for no range
                            if (scope.min === scope.max && modelMin() == modelMax()) {

                                // reposition handles
                                angular.element(handles[0]).css(pos, '0%');
                                angular.element(handles[1]).css(pos, '100%');

                                if (scope.attachHandleValues) {
                                    // reposition values
                                    angular.element(values[0]).css(pos, '0%');
                                    angular.element(values[1]).css(pos, '100%');
                                }

                                // reposition join
                                angular.element(join).css(pos, '0%').css(posOpp, '0%');

                            } else {

                                // reposition handles
                                angular.element(handles[0]).css(pos, handle1pos + '%');
                                angular.element(handles[1]).css(pos, handle2pos + '%');

                                if (scope.attachHandleValues) {
                                    // reposition values
                                    angular.element(values[0]).css(pos, value1pos + '%');
                                    angular.element(values[1]).css(pos, value2pos + '%');
                                    angular.element(values[1]).css(posOpp, 'auto');
                                }

                                // reposition join
                                angular.element(join).css(pos, handle1pos + '%').css(posOpp, (100 - handle2pos) + '%');

                                // ensure min handle can't be hidden behind max handle
                                if (handle1pos > 95) {
                                    angular.element(handles[0]).css('z-index', 3);
                                }
                            }

                        }

                    }

                    function handleMove(index) {

                        var $handle = handles[index];

                        // on mousedown / touchstart
                        $handle.bind(onEvent + 'X', function(event) {

                            var handleDownClass = (index === 0 ? 'ngrs-handle-min' : 'ngrs-handle-max') + '-down',
                                //unbind = $handle.add($document).add('body'),
                                modelValue = (index === 0 ? modelMin() : modelMax()) - scope.min,
                                originalPosition = (modelValue / range) * 100,
                                originalClick = client(event),
                                previousClick = originalClick,
                                previousProposal = false;

                            if (angular.isFunction(scope.onHandleDown)) {
                                scope.onHandleDown();
                            }

                            // stop user accidentally selecting stuff
                            angular.element('body').bind('selectstart' + eventNamespace, function() {
                                return false;
                            });

                            // only do stuff if we are disabled
                            if (!scope.disabled) {

                                // flag as down
                                down = true;

                                // add down class
                                $handle.addClass('ngrs-down');

                                $slider.addClass('ngrs-focus ' + handleDownClass);

                                // add touch class for MS styling
                                angular.element('body').addClass('ngrs-touching');

                                // listen for mousemove / touchmove document events
                                $document.bind(moveEvent, function(e) {
                                    // prevent default
                                    e.preventDefault();

                                    var currentClick = client(e),
                                        movement,
                                        proposal,
                                        other,
                                        per = (scope.step / range) * 100,
                                        otherModelPosition = (((index === 0 ? modelMax() : modelMin()) - scope.min) / range) * 100;

                                    if (currentClick[0] === "x") {
                                        return;
                                    }

                                    // calculate deltas
                                    currentClick[0] -= originalClick[0];
                                    currentClick[1] -= originalClick[1];

                                    // has movement occurred on either axis?
                                    movement = [
                                        (previousClick[0] !== currentClick[0]), (previousClick[1] !== currentClick[1])
                                    ];

                                    // propose a movement
                                    proposal = originalPosition + ((currentClick[orientation] * 100) / (orientation ? $slider.height() : $slider.width()));

                                    // normalize so it can't move out of bounds
                                    proposal = restrict(proposal);

                                    if (scope.preventEqualMinMax) {

                                        if (per === 0) {
                                            per = (1 / range) * 100; // restrict to 1
                                        }

                                        if (index === 0) {
                                            otherModelPosition = otherModelPosition - per;
                                        } else if (index === 1) {
                                            otherModelPosition = otherModelPosition + per;
                                        }
                                    }

                                    // check which handle is being moved and add / remove margin
                                    if (index === 0) {
                                        proposal = proposal > otherModelPosition ? otherModelPosition : proposal;
                                    } else if (index === 1) {
                                        proposal = proposal < otherModelPosition ? otherModelPosition : proposal;
                                    }

                                    if (scope.step > 0) {
                                        // only change if we are within the extremes, otherwise we get strange rounding
                                        if (proposal < 100 && proposal > 0) {
                                            proposal = Math.round(proposal / per) * per;
                                        }
                                    }

                                    if (proposal > 95 && index === 0) {
                                        $handle.css('z-index', 3);
                                    } else {
                                        $handle.css('z-index', '');
                                    }

                                    if (movement[orientation] && proposal != previousProposal) {

                                        if (index === 0) {

                                            // update model as we slide
                                            modelMin(parseFloat(parseFloat((((proposal * range) / 100) + scope.min)).toFixed(scope.decimalPlaces)));

                                        } else if (index === 1) {

                                            modelMax(parseFloat(parseFloat((((proposal * range) / 100) + scope.min)).toFixed(scope.decimalPlaces)));
                                        }

                                        // update angular
                                        scope.$apply();

                                        previousProposal = proposal;

                                    }

                                    previousClick = currentClick;

                                }).bind(offEvent, function() {

                                    if (angular.isFunction(scope.onHandleUp)) {
                                        scope.onHandleUp();
                                    }

                                    // unbind listeners
                                    $document.off(moveEvent);
                                    $document.off(offEvent);

                                    angular.element('body').removeClass('ngrs-touching');

                                    // cancel down flag
                                    down = false;
//                                    console.log('rangeSlider.js off');
                                    
                                    var event = new Event('rangeSliderOff');
                                    // Dispatch the event.
                                    window.dispatchEvent(event);
                                             
                                    // remove down and over class
                                    $handle.removeClass('ngrs-down');
                                    $handle.removeClass('ngrs-over');

                                    // remove active class
                                    $slider.removeClass('ngrs-focus ' + handleDownClass);

                                });
                            }

                        }).on(overEvent, function () {
                            $handle.addClass('ngrs-over');
                        }).on(outEvent, function () {
                            if (!down) {
                                $handle.removeClass('ngrs-over');
                            }
                        });
                    }

                    function throwError(message) {
                        scope.disabled = true;
                        throw new Error('RangeSlider: ' + message);
                    }

                    function throwWarning(message) {
                        $log.warn(message);
                    }

                    /**
                     * DESTROY
                     */

                    scope.$on('$destroy', function() {

                        // unbind event from slider
                        $slider.off(eventNamespace);

                        // unbind from body
                        angular.element('body').off(eventNamespace);

                        // unbind from document
                        $document.off(eventNamespace);

                        // unbind from handles
                        for (var i = 0, l = handles.length; i < l; i++) {
                            handles[i].off(eventNamespace);
                            handles[i].off(eventNamespace + 'X');
                        }

                    });

                    /**
                     * INIT
                     */

                    $slider
                    // disable selection
                        .bind('selectstart' + eventNamespace, function(event) {
                            return false;
                        })
                        // stop propagation
                        .bind('click', function(event) {
                            event.stopPropagation();
                        });

                    // bind events to each handle
                    handleMove(0);
                    handleMove(1);

                }
            };
        }]);

    // requestAnimationFramePolyFill
    // http://www.paulirish.com/2011/requestanimationframe-for-smart-animating/
    // shim layer with setTimeout fallback
    window.requestAnimFrame = (function() {
        return window.requestAnimationFrame ||
            window.webkitRequestAnimationFrame ||
            window.mozRequestAnimationFrame ||
            function(callback) {
                window.setTimeout(callback, 1000 / 60);
            };
    })();
}());
