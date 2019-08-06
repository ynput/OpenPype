/*

 Copyright (C) 2015 Ivan Maeder

 This program is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program.  If not, see <http://www.gnu.org/licenses/>.

 -

 Prevent computer or display sleep with HTML5/JavaScript. Include this
 file then use the following:

     sleep.prevent()
     sleep.allow()

 */
var sleep = {
    prevent: function() {
        if (!this._video) {
            this._init();
        }

        this._video.setAttribute('loop', 'loop');
        this._video.play();
    },
    allow: function() {
        if (!this._video) {
            return;
        }

        this._video.removeAttribute('loop');
        this._video.pause();
    },
    _init: function() {
        this._video = document.createElement('video');
        this._video.setAttribute('width', '10');
        this._video.setAttribute('height', '10');
        this._video.style.position = 'absolute';
        this._video.style.top = '-10px';
        this._video.style.left = '-10px';

        var source_mp4 = document.createElement('source');
        source_mp4.setAttribute('src', 'https://github.com/ivanmaeder/computer-sleep/raw/master/resources/muted-blank.mp4');
        source_mp4.setAttribute('type', 'video/mp4');
        this._video.appendChild(source_mp4);

        var source_ogg = document.createElement('source');
        source_ogg.setAttribute('src', 'https://github.com/ivanmaeder/computer-sleep/raw/master/resources/muted-blank.ogv');
        source_ogg.setAttribute('type', 'video/ogg');
        this._video.appendChild(source_ogg);

        document.body.appendChild(this._video);
    },
    _video: null
}
