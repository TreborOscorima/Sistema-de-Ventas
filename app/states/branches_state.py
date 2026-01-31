import reflex as rx
from typing import List, Dict, Any
from sqlmodel import select
from sqlalchemy import func
from sqlalchemy.orm import selectinload

from app.models import Branch, User as UserModel, UserBranch, Sale, Purchase, CashboxSession, Product
from app.utils.db_seeds import seed_new_branch_data
from .mixin_state import MixinState


class BranchesState(MixinState):
    branches_list: List[Dict[str, Any]] = []
    new_branch_name: str = ""
    new_branch_address: str = ""

    editing_branch_id: str = ""
    editing_branch_name: str = ""
    editing_branch_address: str = ""

    branch_users_modal_open: bool = False
    branch_users_branch_id: str = ""
    branch_users_branch_name: str = ""
    branch_users_rows: List[Dict[str, Any]] = []

    def _require_manage_config(self):
        if hasattr(self, "current_user") and not self.current_user["privileges"].get(
            "manage_config"
        ):
            return rx.toast("No tiene permisos para configurar el sistema.", duration=3000)
        return None

    def load_branches(self):
        company_id = self._company_id()
        if not company_id:
            self.branches_list = []
            return
        with rx.session() as session:
            branches = session.exec(
                select(Branch).where(Branch.company_id == company_id).order_by(Branch.name)
            ).all()
            counts = dict(
                session.exec(
                    select(UserBranch.branch_id, func.count(UserBranch.user_id))
                    .join(Branch, Branch.id == UserBranch.branch_id)
                    .where(Branch.company_id == company_id)
                    .group_by(UserBranch.branch_id)
                ).all()
            )
        self.branches_list = [
            {
                "id": str(branch.id),
                "name": branch.name,
                "address": branch.address,
                "users_count": int(counts.get(branch.id, 0)),
            }
            for branch in branches
        ]

    @rx.event
    def set_new_branch_name(self, value: str):
        self.new_branch_name = value or ""

    @rx.event
    def set_new_branch_address(self, value: str):
        self.new_branch_address = value or ""

    @rx.event
    def handle_branch_name_change(self, value: str):
        if self.editing_branch_id:
            self.editing_branch_name = value or ""
        else:
            self.new_branch_name = value or ""

    @rx.event
    def handle_branch_address_change(self, value: str):
        if self.editing_branch_id:
            self.editing_branch_address = value or ""
        else:
            self.new_branch_address = value or ""

    @rx.event
    def create_branch(self):
        toast = self._require_manage_config()
        if toast:
            return toast
        company_id = self._company_id()
        if not company_id:
            return rx.toast("Empresa no definida.", duration=3000)
        name = (self.new_branch_name or "").strip()
        address = (self.new_branch_address or "").strip()
        if not name:
            return rx.toast("Ingrese el nombre de la sucursal.", duration=2500)
        with rx.session() as session:
            existing = session.exec(
                select(Branch)
                .where(Branch.company_id == company_id)
                .where(Branch.name == name)
            ).first()
            if existing:
                return rx.toast("Ya existe una sucursal con ese nombre.", duration=2500)
            branch = Branch(company_id=company_id, name=name, address=address)
            session.add(branch)
            session.flush()
            user_id = self.current_user.get("id") if hasattr(self, "current_user") else None
            if user_id:
                session.add(UserBranch(user_id=int(user_id), branch_id=branch.id))
            seed_new_branch_data(session, company_id, branch.id)
            session.commit()
        self.new_branch_name = ""
        self.new_branch_address = ""
        self.load_branches()
        return rx.toast("Sucursal creada.", duration=2500)

    @rx.event
    def start_edit_branch(self, branch_id: str):
        company_id = self._company_id()
        if not company_id:
            return
        with rx.session() as session:
            branch = session.exec(
                select(Branch)
                .where(Branch.id == int(branch_id))
                .where(Branch.company_id == company_id)
            ).first()
            if not branch:
                return rx.toast("Sucursal no encontrada.", duration=2500)
            self.editing_branch_id = str(branch.id)
            self.editing_branch_name = branch.name or ""
            self.editing_branch_address = branch.address or ""

    @rx.event
    def set_editing_branch_name(self, value: str):
        self.editing_branch_name = value or ""

    @rx.event
    def set_editing_branch_address(self, value: str):
        self.editing_branch_address = value or ""

    @rx.event
    def cancel_edit_branch(self):
        self.editing_branch_id = ""
        self.editing_branch_name = ""
        self.editing_branch_address = ""

    @rx.event
    def save_branch(self):
        toast = self._require_manage_config()
        if toast:
            return toast
        company_id = self._company_id()
        if not company_id:
            return rx.toast("Empresa no definida.", duration=3000)
        if not self.editing_branch_id:
            return
        name = (self.editing_branch_name or "").strip()
        address = (self.editing_branch_address or "").strip()
        if not name:
            return rx.toast("Ingrese el nombre de la sucursal.", duration=2500)
        branch_id = int(self.editing_branch_id)
        with rx.session() as session:
            existing = session.exec(
                select(Branch)
                .where(Branch.company_id == company_id)
                .where(Branch.name == name)
                .where(Branch.id != branch_id)
            ).first()
            if existing:
                return rx.toast("Ya existe una sucursal con ese nombre.", duration=2500)
            branch = session.exec(
                select(Branch)
                .where(Branch.company_id == company_id)
                .where(Branch.id == branch_id)
            ).first()
            if not branch:
                return rx.toast("Sucursal no encontrada.", duration=2500)
            branch.name = name
            branch.address = address
            session.add(branch)
            session.commit()
        self.cancel_edit_branch()
        self.load_branches()
        return rx.toast("Sucursal actualizada.", duration=2500)

    @rx.event
    def delete_branch(self, branch_id: str):
        toast = self._require_manage_config()
        if toast:
            return toast
        company_id = self._company_id()
        if not company_id:
            return rx.toast("Empresa no definida.", duration=3000)
        if not branch_id:
            return
        branch_id_int = int(branch_id)
        current_branch = self._branch_id()
        with rx.session() as session:
            total_branches = session.exec(
                select(func.count(Branch.id)).where(Branch.company_id == company_id)
            ).one()
            if total_branches and int(total_branches) <= 1:
                return rx.toast("No puedes eliminar la única sucursal.", duration=3000)
            if current_branch and int(current_branch) == branch_id_int:
                return rx.toast("No puedes eliminar la sucursal activa.", duration=3000)
            if session.exec(
                select(Sale.id).where(Sale.branch_id == branch_id_int)
            ).first():
                return rx.toast("No puedes eliminar una sucursal con ventas.", duration=3000)
            if session.exec(
                select(Purchase.id).where(Purchase.branch_id == branch_id_int)
            ).first():
                return rx.toast("No puedes eliminar una sucursal con compras.", duration=3000)
            if session.exec(
                select(CashboxSession.id).where(CashboxSession.branch_id == branch_id_int)
            ).first():
                return rx.toast("No puedes eliminar una sucursal con caja registrada.", duration=3000)
            if session.exec(
                select(Product.id).where(Product.branch_id == branch_id_int)
            ).first():
                return rx.toast("No puedes eliminar una sucursal con inventario.", duration=3000)

            branch = session.exec(
                select(Branch)
                .where(Branch.company_id == company_id)
                .where(Branch.id == branch_id_int)
            ).first()
            if not branch:
                return rx.toast("Sucursal no encontrada.", duration=2500)
            for member in session.exec(
                select(UserBranch).where(UserBranch.branch_id == branch_id_int)
            ).all():
                session.delete(member)
            session.delete(branch)
            session.commit()
        self.load_branches()
        return rx.toast("Sucursal eliminada.", duration=2500)

    @rx.event
    def open_branch_users(self, branch_id: str):
        toast = self._require_manage_config()
        if toast:
            return toast
        company_id = self._company_id()
        if not company_id:
            return rx.toast("Empresa no definida.", duration=3000)
        branch_id_int = int(branch_id)
        with rx.session() as session:
            branch = session.exec(
                select(Branch)
                .where(Branch.company_id == company_id)
                .where(Branch.id == branch_id_int)
            ).first()
            if not branch:
                return rx.toast("Sucursal no encontrada.", duration=2500)
            users = session.exec(
                select(UserModel)
                .where(UserModel.company_id == company_id)
                .options(selectinload(UserModel.role))
                .order_by(UserModel.username)
            ).all()
            existing = session.exec(
                select(UserBranch.user_id).where(UserBranch.branch_id == branch_id_int)
            ).all()
            existing_ids = {int(row) for row in existing if row}
            rows = []
            for user in users:
                rows.append(
                    {
                        "id": user.id,
                        "username": user.username,
                        "role": user.role.name if user.role else "Sin rol",
                        "email": getattr(user, "email", "") or "",
                        "has_access": user.id in existing_ids,
                        "is_default": getattr(user, "branch_id", None) == branch_id_int,
                    }
                )
            self.branch_users_rows = rows
            self.branch_users_branch_id = str(branch.id)
            self.branch_users_branch_name = branch.name or ""
            self.branch_users_modal_open = True

    @rx.event
    def set_branch_user_access(self, user_id: int, value: bool):
        updated = []
        for row in self.branch_users_rows:
            if int(row["id"]) == int(user_id):
                if row.get("is_default") and not value:
                    updated.append({**row, "has_access": True})
                else:
                    updated.append({**row, "has_access": bool(value)})
            else:
                updated.append(row)
        self.branch_users_rows = updated

    @rx.event
    def close_branch_users(self):
        self.branch_users_modal_open = False
        self.branch_users_branch_id = ""
        self.branch_users_branch_name = ""
        self.branch_users_rows = []

    @rx.event
    def save_branch_users(self):
        toast = self._require_manage_config()
        if toast:
            return toast
        if not self.branch_users_branch_id:
            return
        branch_id = int(self.branch_users_branch_id)
        company_id = self._company_id()
        if not company_id:
            return rx.toast("Empresa no definida.", duration=3000)
        desired_ids = {
            int(row["id"]) for row in self.branch_users_rows if row.get("has_access")
        }
        with rx.session() as session:
            existing = session.exec(
                select(UserBranch).where(UserBranch.branch_id == branch_id)
            ).all()
            existing_ids = {int(row.user_id) for row in existing}

            to_add = desired_ids - existing_ids
            to_remove = existing_ids - desired_ids

            for user_id in to_add:
                session.add(UserBranch(user_id=user_id, branch_id=branch_id))

            if to_remove:
                default_users = {
                    int(u.id)
                    for u in session.exec(
                        select(UserModel.id)
                        .where(UserModel.company_id == company_id)
                        .where(UserModel.branch_id == branch_id)
                    ).all()
                }
                for member in existing:
                    if member.user_id in to_remove:
                        if member.user_id in default_users:
                            continue
                        session.delete(member)
            session.commit()
        self.load_branches()
        self.close_branch_users()
        return rx.toast("Accesos actualizados.", duration=2500)
