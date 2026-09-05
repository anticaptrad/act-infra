-- anticaptrad: isolated namespace inside the shared auth project
create schema if not exists anticaptrad;
revoke all on schema anticaptrad from public;
