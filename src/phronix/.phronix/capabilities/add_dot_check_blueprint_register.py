def register(self, app: "Flask", options: dict) -> None:
    """Called by :meth:`Flask.register_blueprint` to register all
    views and callbacks registered on the blueprint with the
    application. Creates a :class:`.BlueprintSetupState` and calls
    each :meth:`record` callbackwith it.

    :param app: The application this blueprint is being registered
        with.
    :param options: Keyword arguments forwarded from
        :meth:`~Flask.register_blueprint`.
    :param first_registration: Whether this is the first time this
        blueprint has been registered on the application.
    """
    first_registration = False

    if self.name in app.blueprints:
        assert app.blueprints[self.name] is self, (
            "A name collision occurred between blueprints"
            f" {self!r} and {app.blueprints[self.name]!r}."
            f" Both share the same name {self.name!r}."
            f" Blueprints that are created on the fly need unique"
            f" names."
        )
    else:
        app.blueprints[self.name] = self
        first_registration = True

    self._got_registered_once = True
    state = self.make_setup_state(app, options, first_registration)

    if self.has_static_folder:
        state.add_url_rule(
            f"{self.static_url_path}/<path:filename>",
            view_func=self.send_static_file,
            endpoint="static",
        )

    # Merge blueprint data into parent.
    if first_registration:

        def extend(bp_dict, parent_dict):
            for key, values in bp_dict.items():
                key = self.name if key is None else f"{self.name}.{key}"

                parent_dict[key].extend(values)

        for key, value in self.error_handler_spec.items():
            key = self.name if key is None else f"{self.name}.{key}"
            value = defaultdict(
                dict,
                {
                    code: {
                        exc_class: func for exc_class, func in code_values.items()
                    }
                    for code, code_values in value.items()
                },
            )
            app.error_handler_spec[key] = value

        for endpoint, func in self.view_functions.items():
            app.view_functions[endpoint] = func

        extend(self.before_request_funcs, app.before_request_funcs)
        extend(self.after_request_funcs, app.after_request_funcs)
        extend(
            self.teardown_request_funcs,
            app.teardown_request_funcs,
        )
        extend(self.url_default_functions, app.url_default_functions)
        extend(self.url_value_preprocessors, app.url_value_preprocessors)
        extend(self.template_context_processors, app.template_context_processors)

    for deferred in self.deferred_functions:
        deferred(state)