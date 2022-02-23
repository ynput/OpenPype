//////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////
//
//                            openHarmony Library v0.01
//
//
//         Developped by Mathieu Chaptel, Chris Fourney...
//
//
//   This library is an open source implementation of a Document Object Model
//   for Toonboom Harmony. It also implements patterns similar to JQuery
//   for traversing this DOM.
//
//   Its intended purpose is to simplify and streamline toonboom scripting to
//   empower users and be easy on newcomers, with default parameters values,
//   and by hiding the heavy lifting required by the official API.
//
//   This library is provided as is and is a work in progress. As such, not every
//   function has been implemented or is garanteed to work. Feel free to contribute
//   improvements to its official github. If you do make sure you follow the provided
//   template and naming conventions and document your new methods properly.
//
//   This library doesn't overwrite any of the objects and classes of the official
//   Toonboom API which must remains available.
//
//   This library is made available under the MIT license.
//   https://opensource.org/licenses/mit
//
//   The repository for this library is available at the address:
//   https://github.com/cfourney/OpenHarmony/
//
//
//   For any requests feel free to contact m.chaptel@gmail.com
//
//
//
//
//////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////


//TODO : view.currentToolManager integration.


//////////////////////////////////////
//////////////////////////////////////
//                                  //
//                                  //
//           $.oUtils class         //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////


/**
 * The $.oUtils helper class -- providing generic utilities. Doesn't need instanciation.
 * @classdesc  $.oUtils utility Class
 */
$.oUtils = function(){
    this._type = "utils";
}

/**
 * Finds the longest common substring between two strings.
 * @param   {string}   str1
 * @param   {string}   str2
 * @returns {string} the found string
 */
$.oUtils.longestCommonSubstring = function( str1, str2 ){
	if (!str1 || !str2)
		return {
			length: 0,
			sequence: "",
			offset: 0
		};

	var sequence = "",
		str1Length = str1.length,
		str2Length = str2.length,
		num = new Array(str1Length),
		maxlen = 0,
		lastSubsBegin = 0;

	for (var i = 0; i < str1Length; i++) {
		var subArray = new Array(str2Length);
		for (var j = 0; j < str2Length; j++)
			subArray[j] = 0;
		num[i] = subArray;
	}
	var subsBegin = null;
	for (var i = 0; i < str1Length; i++){
		for (var j = 0; j < str2Length; j++){
			if (str1[i] !== str2[j]){
				num[i][j] = 0;
			}else{
				if ((i === 0) || (j === 0)){
					num[i][j] = 1;
				}else{
					num[i][j] = 1 + num[i - 1][j - 1];
        }
				if (num[i][j] > maxlen){
					maxlen = num[i][j];
					subsBegin = i - num[i][j] + 1;
					if (lastSubsBegin === subsBegin){//if the current LCS is the same as the last time this block ran
						sequence += str1[i];
					}else{
            //this block resets the string builder if a different LCS is found
						lastSubsBegin = subsBegin;
						sequence= ""; //clear it
						sequence += str1.substr(lastSubsBegin, (i + 1) - lastSubsBegin);
					}
				}
			}
		}
	}
	return {
		length: maxlen,
		sequence: sequence,
		offset: subsBegin
	};
}
