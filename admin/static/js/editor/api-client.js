/**
 * ApiClient — unified HTTP wrapper for draft editor endpoints.
 * Features: auto-retry (2x), JSON body, JWT auth from cookie.
 */
var ApiClient = (function() {

  function ApiClient() {
    this.baseUrl = '/admin/site-builder/api/draft';
    this.retryCount = 2;
    this.retryDelay = 1000;
  }

  /** Get JWT token from sso_token cookie */
  function getToken() {
    var match = document.cookie.match(/(?:^|;\s*)sso_token=([^;]*)/);
    return match ? match[1] : '';
  }

  /** POST JSON, returns parsed response */
  ApiClient.prototype._post = function(path, body) {
    var self = this;
    return new Promise(function(resolve, reject) {
      function attempt(n) {
        fetch(self.baseUrl + path, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + getToken()
          },
          body: JSON.stringify(body)
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
          if (data && data.success === false) {
            reject(data.error || 'Unknown API error');
          } else {
            resolve(data);
          }
        })
        .catch(function(err) {
          if (n < self.retryCount) {
            setTimeout(function() { attempt(n + 1); }, self.retryDelay);
          } else {
            reject(err);
          }
        });
      }
      attempt(0);
    });
  };

  /** Upload file via multipart/form-data */
  ApiClient.prototype.upload = function(path, formData) {
    var self = this;
    return new Promise(function(resolve, reject) {
      var xhr = new XMLHttpRequest();
      xhr.open('POST', self.baseUrl + path);
      xhr.setRequestHeader('Authorization', 'Bearer ' + getToken());
      xhr.onload = function() {
        try {
          var data = JSON.parse(xhr.responseText);
          if (data && data.success === false) {
            reject(data.error || 'Upload failed');
          } else {
            resolve(data);
          }
        } catch(e) { reject('Invalid response'); }
      };
      xhr.onerror = function() { reject('Network error'); };
      xhr.send(formData);
    });
  };

  /* ── Convenience methods ── */

  ApiClient.prototype.updateBlock = function(blockId, field, value, scope) {
    return this._post('/update-block', {
      block_id: blockId, field: field, value: value, scope: scope || 'block'
    });
  };

  ApiClient.prototype.updateBlockOrder = function(order) {
    return this._post('/update-block-order', { order: order });
  };

  ApiClient.prototype.deleteBlock = function(blockId) {
    return this._post('/delete-block', { block_id: blockId });
  };

  ApiClient.prototype.addBlock = function(page, position, blockType, title, content, icon) {
    return this._post('/add-block', {
      page: page, position: position, block_type: blockType,
      title: title, content: content, icon: icon
    });
  };

  ApiClient.prototype.updateTokens = function(scope, data) {
    return this._post('/update-tokens', { scope: scope, data: data });
  };

  ApiClient.prototype.uploadImage = function(blockId, field, file) {
    var fd = new FormData();
    fd.append('file', file);
    fd.append('block_id', blockId || '');
    fd.append('field', field || 'image_url');
    return this.upload('/upload-image', fd);
  };

  return ApiClient;
})();
