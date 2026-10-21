from django import forms

INPUT = (
    "block w-full rounded-lg border border-slate-300 bg-white px-3.5 py-2.5 text-sm text-slate-900 "
    "placeholder-slate-400 focus:border-brand-500 focus:ring-2 focus:ring-brand-500/25 focus:outline-none "
    "aria-[invalid=true]:border-red-400 aria-[invalid=true]:ring-red-200 disabled:bg-slate-100"
)
CHECKBOX = "mt-0.5 h-4 w-4 shrink-0 rounded border-slate-300 text-brand-500 focus:ring-brand-500"
FILE = (
    "block w-full text-sm text-slate-600 file:mr-4 file:cursor-pointer file:rounded-lg file:border-0 "
    "file:bg-brand-50 file:px-4 file:py-2.5 file:text-sm file:font-semibold file:text-brand-700 hover:file:bg-brand-100"
)


class CascadeSelect(forms.Select):
    """
    Üst alana bağlı select. Her seçeneğe `data-parent` eklenir; static/js/cascade.js
    üst alan değişince seçenekleri süzer. parent_map: {seçenek_pk: üst_pk}
    """

    def __init__(self, parent, attrs=None, choices=()):
        super().__init__(attrs, choices)
        self.attrs["data-cascade-parent"] = parent
        self.parent_map = {}

    def __deepcopy__(self, memo):
        obj = super().__deepcopy__(memo)
        obj.parent_map = dict(self.parent_map)
        return obj

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        parent = self.parent_map.get(str(value))
        if parent is not None:
            option["attrs"]["data-parent"] = str(parent)
        return option


class TailwindFormMixin:
    """Tüm widget'lara Lotus temasına uygun Tailwind sınıfları uygular."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.ClearableFileInput):  # "Currently/Clear" arayüzü yerine sade input
                widget = forms.FileInput(attrs=widget.attrs)
                widget.is_required = field.required
                field.widget = widget
            if isinstance(widget, (forms.CheckboxInput, forms.CheckboxSelectMultiple)):
                css = CHECKBOX
            elif isinstance(widget, forms.FileInput):
                css = FILE
            else:
                css = INPUT
                if isinstance(widget, forms.Textarea):
                    widget.attrs.setdefault("rows", 3)
                if isinstance(widget, forms.DateInput):
                    widget.input_type = "date"
                    widget.format = "%Y-%m-%d"
            widget.attrs["class"] = f"{widget.attrs.get('class', '')} {css}".strip()
            if isinstance(field, forms.ImageField):  # yüklemeden önce önizleme (Alpine)
                widget.attrs["x-on:change"] = "src = $event.target.files[0] ? URL.createObjectURL($event.target.files[0]) : null"
