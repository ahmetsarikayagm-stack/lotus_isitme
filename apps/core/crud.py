"""
Genel amaçlı CRUD altyapısı.

Her modül, `CrudConfig` alt sınıfı tanımlar; liste (arama / filtre / sıralama / sayfalama),
ekle, düzenle, sil ve toplu sil sayfaları buradan otomatik üretilir:

    class PatientCrud(CrudConfig):
        model = Patient
        ...

    # urls.py
    app_name = "patients"
    urlpatterns = PatientCrud.urls()
"""
import json
from dataclasses import dataclass
from typing import Callable, Iterable

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import ProtectedError, Q
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import path, reverse
from django.utils.safestring import mark_safe
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from apps.accounts.mixins import ModuleAccessMixin

PROTECTED_MSG = "Bu kayıt başka kayıtlarda kullanıldığı için silinemez."


class CrudError(Exception):
    """İş kuralı hatası; mesajı kullanıcıya gösterilir (form hatası veya uyarı olarak)."""


@dataclass(frozen=True)
class Col:
    """Liste sütunu. kind: text | money | date | datetime | bool | image | file | qty | badge"""
    label: str
    path: str                 # "created_by.display_name" gibi nokta yolu
    sort: str | None = None   # sıralama için ORM yolu (None = sıralanamaz)
    kind: str = "text"
    link: bool = False        # hücre düzenleme sayfasına link olsun


@dataclass(frozen=True)
class Filter:
    param: str
    label: str
    lookup: str
    choices: Callable[[], Iterable[tuple[str, str]]] | None = None
    kind: str = "select"      # select | date


@dataclass(frozen=True)
class RowAction:
    """Listede her satırın yanında görünen ek bağlantı (örn. PDF / Excel). url_name: pk alan URL adı."""
    label: str
    url_name: str
    title: str = ""
    tone: str = "slate"     # slate | red | green
    new_tab: bool = False


@dataclass(frozen=True)
class Card:
    """Ekle/Düzenle formundaki kart."""
    title: str
    fields: tuple
    description: str = ""
    columns: int = 2


def choices_from(model, label=str, **filters):
    def _choices():
        return [(str(o.pk), label(o)) for o in model.objects.filter(**filters)]
    return _choices


def resolve(obj, dotted: str):
    for part in dotted.split("."):
        if obj is None:
            return None
        obj = getattr(obj, part, None)
        if callable(obj):
            obj = obj()
    return obj


class CrudConfig:
    model = None
    form_class = None
    module_key = ""
    namespace = ""
    singular = ""
    plural = ""
    columns: tuple = ()
    search_fields: tuple = ()
    search_placeholder = "Ara..."
    filters: tuple = ()
    ordering: tuple = ("-pk",)
    select_related: tuple = ()
    paginate_by = 15
    cards: tuple = ()
    list_template = "core/list.html"
    form_template = "core/form.html"
    formset_class = None  # satır (alt kayıt) formu gerekiyorsa inline formset sınıfı
    row_actions: tuple = ()  # listede her satıra eklenen RowAction'lar

    @classmethod
    def get_queryset(cls, request):
        qs = cls.model.objects.all()
        if cls.select_related:
            qs = qs.select_related(*cls.select_related)
        return qs

    # --- Özelleştirme noktaları (hook) ---
    @classmethod
    def initial(cls, request) -> dict:
        """Yeni kayıt formunun başlangıç değerleri."""
        return {}

    @classmethod
    def form_kwargs(cls, request) -> dict:
        """Forma ek parametre geçmek için."""
        return {}

    @classmethod
    def list_context(cls, request) -> dict:
        """Liste şablonuna eklenecek ek bağlam."""
        return {}

    @classmethod
    def form_context(cls, request, obj) -> dict:
        """Ekle/Düzenle şablonuna eklenecek ek bağlam (obj: düzenlemede kayıt, yeni kayıtta None)."""
        return {}

    @classmethod
    def formset_kwargs(cls, request, obj) -> dict:
        """Formset oluştururken ek parametreler (form_kwargs vb.). obj: düzenlemede kayıt, yeni kayıtta None."""
        return {}

    @classmethod
    def cross_validate(cls, form, formset) -> None:
        """Form ve formset ayrı ayrı geçerliyken, ikisini birlikte ilgilendiren kontroller (form.add_error ile)."""

    @classmethod
    def save_object(cls, request, form, obj, creating, formset=None):
        """Kaydetme mantığı. İş kuralı ihlalinde CrudError fırlatılabilir."""
        obj.save()
        form.save_m2m()

    @classmethod
    def delete_object(cls, request, obj):
        """Silme mantığı. İş kuralı ihlalinde CrudError fırlatılabilir."""
        obj.delete()

    @classmethod
    def url(cls, name, *args):
        return reverse(f"{cls.namespace}:{name}", args=args)

    @classmethod
    def urls(cls):
        return [
            path("", CrudListView.as_view(crud=cls), name="list"),
            path("ekle/", CrudCreateView.as_view(crud=cls), name="create"),
            path("<int:pk>/duzenle/", CrudUpdateView.as_view(crud=cls), name="update"),
            path("<int:pk>/sil/", CrudDeleteView.as_view(crud=cls), name="delete"),
            path("toplu-sil/", CrudBulkDeleteView.as_view(crud=cls), name="bulk_delete"),
        ]


class CrudMixin(ModuleAccessMixin):
    crud = None

    @property
    def module_key(self):
        return self.crud.module_key


# ----------------------------------------------------------------- Liste
class CrudListView(CrudMixin, ListView):
    def get_template_names(self):
        return [self.crud.list_template]

    def get_paginate_by(self, queryset):
        return self.crud.paginate_by

    # -- sorgu
    def get_queryset(self):
        qs = self.crud.get_queryset(self.request)
        return self._order(self._filter(self._search(qs)))

    def _search(self, qs):
        q = self.request.GET.get("q", "").strip()
        if q and self.crud.search_fields:
            for term in q.split():
                cond = Q()
                for field in self.crud.search_fields:
                    cond |= Q(**{f"{field}__icontains": term})
                qs = qs.filter(cond)
        return qs

    def _filter(self, qs):
        for f in self.crud.filters:
            value = self.request.GET.get(f.param, "")
            if value == "":
                continue
            if value in ("true", "false"):
                value = value == "true"
            try:
                qs = qs.filter(**{f.lookup: value})
            except (ValueError, TypeError, ValidationError):
                continue
        return qs

    def _order(self, qs):
        sort = self.request.GET.get("sort", "")
        allowed = {c.sort for c in self.crud.columns if c.sort}
        if sort.lstrip("-") in allowed:
            return qs.order_by(sort, "pk")
        return qs.order_by(*self.crud.ordering)

    # -- şablon verisi
    def _row(self, obj):
        cells = []
        for col in self.crud.columns:
            value = resolve(obj, col.path)
            if value == "" or (hasattr(value, "name") and not value):
                value = None
            cells.append({"kind": col.kind, "value": value, "link": col.link})
        return {
            "pk": obj.pk,
            "cells": cells,
            "edit_url": self.crud.url("update", obj.pk),
            "delete_url": self.crud.url("delete", obj.pk),
            "actions": [
                {"label": a.label, "title": a.title or a.label, "tone": a.tone, "new_tab": a.new_tab,
                 "url": self.crud.url(a.url_name, obj.pk)}
                for a in self.crud.row_actions
            ],
        }

    def _headers(self):
        get = self.request.GET
        current = get.get("sort", "")
        base = get.copy()
        base.pop("page", None)
        headers = []
        for col in self.crud.columns:
            h = {"label": col.label, "sortable": bool(col.sort), "direction": None, "url": ""}
            if col.sort:
                nxt = f"-{col.sort}" if current == col.sort else col.sort
                params = base.copy()
                params["sort"] = nxt
                h["url"] = "?" + params.urlencode()
                h["direction"] = "asc" if current == col.sort else "desc" if current == f"-{col.sort}" else None
            headers.append(h)
        return headers

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        crud, get = self.crud, self.request.GET
        page = ctx["page_obj"]
        rows = [self._row(o) for o in ctx["object_list"]]
        filters = [
            {"param": f.param, "label": f.label, "kind": f.kind, "value": get.get(f.param, ""),
             "choices": list(f.choices()) if f.choices else []}
            for f in crud.filters
        ]
        nopage = get.copy()
        nopage.pop("page", None)
        ctx.update(
            crud=crud,
            rows=rows,
            headers=self._headers(),
            filters=filters,
            q=get.get("q", ""),
            sort=get.get("sort", ""),
            filters_active=bool(get.get("q") or any(get.get(f.param) for f in crud.filters)),
            qs_nopage=nopage.urlencode(),
            page_range=page.paginator.get_elided_page_range(page.number, on_each_side=1, on_ends=1),
            total=page.paginator.count,
            create_url=crud.url("create"),
            bulk_url=crud.url("bulk_delete"),
            pks_json=mark_safe(json.dumps([str(r["pk"]) for r in rows])),
        )
        ctx.update(crud.list_context(self.request))
        return ctx


# ----------------------------------------------------------------- Ekle / Düzenle
class CrudFormMixin(CrudMixin):
    def get_template_names(self):
        return [self.crud.form_template]

    def get_form_class(self):
        return self.crud.form_class

    def get_queryset(self):
        return self.crud.get_queryset(self.request)

    def get_success_url(self):
        return self.crud.url("list")

    def get_initial(self):
        initial = super().get_initial().copy()
        if getattr(self, "object", None) is None:  # yalnızca yeni kayıtta
            fields = self.get_form_class().base_fields
            initial.update({k: v for k, v in self.request.GET.items() if k in fields})
            initial.update(self.crud.initial(self.request))
        return initial

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(self.crud.form_kwargs(self.request))
        return kwargs

    def get_formset(self):
        fc = self.crud.formset_class
        if fc is None:
            return None
        kwargs = {"prefix": "items", **self.crud.formset_kwargs(self.request, self.object)}
        if self.object is not None:
            kwargs["instance"] = self.object
        if self.request.method == "POST":
            kwargs.update(data=self.request.POST, files=self.request.FILES)
        return fc(**kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object() if "pk" in self.kwargs else None
        form = self.get_form()
        self._formset = formset = self.get_formset()
        valid = form.is_valid()
        if formset is not None:
            valid = formset.is_valid() and valid  # ikisi de doğrulansın ki tüm hatalar görünsün
        if valid:
            self.crud.cross_validate(form, formset)
            valid = not form.errors
        return self.form_valid(form) if valid else self.form_invalid(form)

    def get_cards(self, form):
        cards = self.crud.cards or (Card(self.crud.singular, tuple(form.fields)),)
        return [
            {
                "title": c.title,
                "description": c.description,
                "columns": c.columns,
                "fields": [form[n] for n in c.fields if n in form.fields],
            }
            for c in cards
        ]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        is_edit = self.object is not None
        ctx.update(
            crud=self.crud,
            cards=self.get_cards(ctx["form"]),
            is_edit=is_edit,
            title=f"{self.crud.singular} Düzenle" if is_edit else f"Yeni {self.crud.singular}",
            cancel_url=self.crud.url("list"),
        )
        ctx.update(self.crud.form_context(self.request, self.object))
        if self.crud.formset_class is not None:
            ctx["formset"] = getattr(self, "_formset", None) or self.get_formset()
        return ctx

    def form_valid(self, form):
        creating = form.instance.pk is None
        obj = form.save(commit=False)
        if creating and hasattr(obj, "created_by_id") and obj.created_by_id is None:
            obj.created_by = self.request.user
        if hasattr(obj, "updated_by_id"):  # işlemi yapan kullanıcı her kayıtta otomatik yazılır
            obj.updated_by = self.request.user
        try:
            with transaction.atomic():
                self.crud.save_object(self.request, form, obj, creating, formset=getattr(self, "_formset", None))
        except CrudError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        self.object = obj
        messages.success(self.request, f"{self.crud.singular} kaydedildi: {obj}")
        return HttpResponseRedirect(self.get_success_url())


class CrudCreateView(CrudFormMixin, CreateView):
    pass


class CrudUpdateView(CrudFormMixin, UpdateView):
    pass


# ----------------------------------------------------------------- Sil
class CrudDeleteView(CrudMixin, DeleteView):
    def get_template_names(self):
        return ["core/confirm_delete.html"]

    def get_queryset(self):
        return self.crud.get_queryset(self.request)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(crud=self.crud, cancel_url=self.crud.url("list"))
        return ctx

    def form_valid(self, form):
        try:
            with transaction.atomic():
                self.crud.delete_object(self.request, self.object)
        except ProtectedError:
            messages.error(self.request, PROTECTED_MSG)
        except CrudError as exc:
            messages.error(self.request, str(exc))
        else:
            messages.success(self.request, f"{self.crud.singular} silindi: {self.object}")
        return redirect(self.crud.url("list"))


class CrudBulkDeleteView(CrudMixin, View):
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        ids = [i for i in request.POST.getlist("ids") if i.isdigit()]
        deleted = blocked = 0
        for obj in self.crud.get_queryset(request).filter(pk__in=ids):
            try:
                with transaction.atomic():
                    self.crud.delete_object(request, obj)
                deleted += 1
            except (ProtectedError, CrudError):
                blocked += 1
        if deleted:
            messages.success(request, f"{deleted} kayıt silindi.")
        if blocked:
            messages.error(request, f"{blocked} kayıt silinemedi (başka kayıtlarda kullanılıyor veya korumalı).")
        if not ids:
            messages.warning(request, "Hiç kayıt seçilmedi.")
        return redirect(self.crud.url("list"))
