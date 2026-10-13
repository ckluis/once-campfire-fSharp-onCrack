// stripcfg FILE: prints FILE with every item (and impl/trait item, statement, field-less attribute carrier) under #[cfg(test)] blanked out,
// keeping all other lines byte for byte. A file with #![cfg(test)] prints empty. Blanked lines keep their line breaks.
use proc_macro2::Span;
use syn::spanned::Spanned;
use syn::visit::Visit;
use syn::{Attribute, Meta};

fn is_cfg_test(a: &Attribute) -> bool {
    if !a.path().is_ident("cfg") { return false; }
    match &a.meta {
        Meta::List(l) => l.tokens.to_string().trim() == "test",
        _ => false,
    }
}
fn is_test_attr(a: &Attribute) -> bool { a.path().is_ident("test") }

struct V { ranges: Vec<(usize, usize)> }
impl V {
    fn check(&mut self, attrs: &[Attribute], span: Span) -> bool {
        if attrs.iter().any(|a| is_cfg_test(a) || is_test_attr(a)) {
            self.ranges.push((span.start().line, span.end().line));
            true
        } else { false }
    }
}
macro_rules! gate { ($name:ident, $ty:ty, $walk:ident) => {
    fn $name(&mut self, i: &'ast $ty) { if self.check(&i.attrs, i.span()) { return; } syn::visit::$walk(self, i); }
}}
impl<'ast> Visit<'ast> for V {
    gate!(visit_item_mod, syn::ItemMod, visit_item_mod);
    gate!(visit_item_fn, syn::ItemFn, visit_item_fn);
    gate!(visit_item_impl, syn::ItemImpl, visit_item_impl);
    gate!(visit_item_use, syn::ItemUse, visit_item_use);
    gate!(visit_item_const, syn::ItemConst, visit_item_const);
    gate!(visit_item_static, syn::ItemStatic, visit_item_static);
    gate!(visit_item_struct, syn::ItemStruct, visit_item_struct);
    gate!(visit_item_enum, syn::ItemEnum, visit_item_enum);
    gate!(visit_item_trait, syn::ItemTrait, visit_item_trait);
    gate!(visit_item_type, syn::ItemType, visit_item_type);
    gate!(visit_item_macro, syn::ItemMacro, visit_item_macro);
    gate!(visit_impl_item_fn, syn::ImplItemFn, visit_impl_item_fn);
    gate!(visit_impl_item_const, syn::ImplItemConst, visit_impl_item_const);
    gate!(visit_impl_item_type, syn::ImplItemType, visit_impl_item_type);
    gate!(visit_trait_item_fn, syn::TraitItemFn, visit_trait_item_fn);
}
fn main() {
    let path = std::env::args().nth(1).expect("file");
    let src = std::fs::read_to_string(&path).unwrap();
    let file = match syn::parse_file(&src) { Ok(f) => f, Err(e) => { eprintln!("PARSE ERROR {path}: {e}"); std::process::exit(2); } };
    if file.attrs.iter().any(|a| is_cfg_test(a)) { for _ in src.lines() { println!(); } return; }
    let mut v = V { ranges: vec![] };
    v.visit_file(&file);
    let lines: Vec<&str> = src.split('\n').collect();
    let mut out = Vec::new();
    for (i, l) in lines.iter().enumerate() {
        let n = i + 1;
        if v.ranges.iter().any(|&(a, b)| n >= a && n <= b) { out.push(""); } else { out.push(l); }
    }
    print!("{}", out.join("\n"));
}
