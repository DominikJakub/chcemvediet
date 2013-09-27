var _ = require("underscore"),
    languages = require("../locales/languages").languages;

var User = function(o) {
    _.extend(this, o);

    if (typeof this.language == "string")
        this.language = languages[this.language];
}

_.extend(User.prototype, {
    displayName: function () {
        if (this.firstName && this.lastName)
            return this.firstName + " " + this.lastName;
        else if (this.firstName)
            return this.firstName;
        else if (this.lastName)
            return this.lastName;
        else
            return this.email;
    }
})

exports.User = User;